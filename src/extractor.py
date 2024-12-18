import os
import json
import csv
from typing import List, Dict
from pydantic import BaseModel, create_model, ValidationError
from ollama import Client
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from tqdm import tqdm
import dotenv

# Load environment variables
dotenv.load_dotenv()

class DynamicExtractor:
    def __init__(self, 
                 model: str = None, 
                 vision_model: str = None, 
                 host: str = None):
        """
        Initialize the extractor with Ollama client and models
        
        :param model: Text processing model 
        :param vision_model: Image processing model
        :param host: Ollama server host
        """
        # Use environment variables with fallback
        self.host = host or os.getenv('OLLAMA_HOST', 'http://localhost:11434/')
        self.text_model = model or os.getenv('TEXT_MODEL', 'llama3')
        self.vision_model = vision_model or os.getenv('VISION_MODEL', 'llama3.2-vision')

        
        self.client = Client(host=self.host)
        self.console = Console()

    def get_dynamic_model(self, fields: List[dict]) -> BaseModel:
        """Dynamically create a Pydantic model based on user-defined fields."""
        model_fields = {}
        for field in fields:
            field_type = str  # Default type
            if field['type'] == 'int':
                field_type = int
            elif field['type'] == 'float':
                field_type = float
            elif field['type'] == 'bool':
                field_type = bool
            elif 'list' in field['type']:
                inner_type = str  # Default inner type
                if 'int' in field['type']:
                    inner_type = int
                elif 'float' in field['type']:
                    inner_type = float
                elif 'bool' in field['type']:
                    inner_type = bool
                field_type = List[inner_type]

            # Set the default value for optional fields
            default_value = None if field['optional'] else ...
            model_fields[field['name']] = (field_type, default_value)

        return create_model('Entity', **model_fields)

    def _extract_structured_data(self, 
                                 response_content: str, 
                                 model_fields: List[dict], 
                                 input_context: str) -> List[dict]:
        """
        Common method to extract structured data and wrap with input context
        
        :param response_content: JSON content from model response
        :param model_fields: Fields for dynamic model
        :param input_context: Input text or image context
        :return: List of dictionaries with input and response
        """
        Entity = self.get_dynamic_model(model_fields)

        class EntitiesList(BaseModel):
            Entities: list[Entity]
        
        try:
            # Validate and parse JSON response
            extracted_data = EntitiesList.model_validate_json(response_content)
            
            # Wrap results with input context
            return [{
                'input': input_context,
                'response': item.model_dump()
            } for item in extracted_data.Entities]
        
        except ValidationError as exc:
            self.console.print(f"[bold red]Validation Error:[/] {repr(exc.errors()[0]['type'])}")
            return []
        except json.JSONDecodeError as exc:
            self.console.print(f"[bold red]JSON Decode Error:[/] {exc}")
            return []

    def process_text(self, text: str, model_fields: List[dict]) -> List[dict]:
        """
        Process text input and extract structured data
        
        :param text: Input text
        :param model_fields: Fields for dynamic model
        :return: List of dictionaries with input and response
        """
        Entity = self.get_dynamic_model(model_fields)

        class EntitiesList(BaseModel):
            Entities: list[Entity]
        
        # Construct a prompt that guides JSON extraction
        prompt = f"""Extract structured data based on these fields: {', '.join(f['name'] for f in model_fields)}
        Provide output as a JSON-compatible list of objects."""

        try:
            response = self.client.chat(
                model=self.text_model,
                messages=[
                    {'role': 'system', 'content': prompt},
                    {'role': 'user', 'content': text}
                ],
                format=EntitiesList.model_json_schema(),
                options={'temperature': 0}
            )
            
            return self._extract_structured_data(
                response.message.content, 
                model_fields, 
                text
            )
        
        except Exception as e:
            self.console.print(f"[bold red]Error processing text:[/] {e}")
            return []

    def process_image(self, image_path: str, model_fields: List[dict]) -> List[dict]:
        """
        Process image input and extract structured data
        
        :param image_path: Path to image file
        :param model_fields: Fields for dynamic model
        :return: List of dictionaries with input and response
        """
        Entity = self.get_dynamic_model(model_fields)

        class EntitiesList(BaseModel):
            Entities: list[Entity]
        
        # Construct a prompt for image analysis
        prompt = f"""Analyze this image and extract structured data for these fields: {', '.join(f['name'] for f in model_fields)}
        Provide output as a JSON-compatible list of objects."""

        try:
            with open(image_path, 'rb') as img_file:
                response = self.client.chat(
                    model=self.vision_model,
                    messages=[
                        {'role': 'system', 'content': prompt},
                        {'role': 'user', 'content': '', 'images': [img_file.read()]}
                    ],
                    format=EntitiesList.model_json_schema(),
                    options={'temperature': 0}
                )
            
            return self._extract_structured_data(
                response.message.content, 
                model_fields, 
                os.path.basename(image_path)
            )
        
        except Exception as e:
            self.console.print(f"[bold red]Error processing image:[/] {e}")
            return []

    def process_bulk_text(self, file_path: str, model_fields: List[dict]) -> List[dict]:
        """
        Process bulk text from .txt or .csv files
        
        :param file_path: Path to text file
        :param model_fields: Fields for dynamic model
        :return: List of dictionaries with input and response
        """
        file_ext = os.path.splitext(file_path)[1].lower()
        results = []

        try:
            if file_ext == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    texts = f.read().split(',,')  # Split by double newline
                    # Use tqdm to show progress for processing texts
                    for text in tqdm(texts, desc="Processing Texts..", unit="text"):
                        if text.strip():  # Ignore empty texts
                            text_results = self.process_text(text, model_fields)
                            results.extend(text_results)

            elif file_ext == '.csv':
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    # Convert the reader to a list to get length for tqdm
                    rows = list(reader)
                    # Use tqdm to show progress for processing rows
                    for row in tqdm(rows, desc="Processing Rows...", unit="row"):
                        text = ' '.join(row)
                        if text.strip():  # Ignore empty rows
                            text_results = self.process_text(text, model_fields)
                            results.extend(text_results)
            
            return results
        
        except Exception as e:
            self.console.print(f"[bold red]Error processing bulk text:[/] {e}")
            return []

    def process_bulk_images(self, folder_path: str, model_fields: List[dict]) -> List[dict]:
        """
        Process multiple images from a folder
        
        :param folder_path: Path to image folder
        :param model_fields: Fields for dynamic model
        :return: List of dictionaries with input and response
        """
        results = []

        try:
            # Get a list of image files in the specified folder
            image_files = [filename for filename in os.listdir(folder_path) 
                        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]

            # Use tqdm to show progress for processing images
            for filename in tqdm(image_files, desc="Processing Images...", unit="image"):
                image_path = os.path.join(folder_path, filename)
                image_results = self.process_image(image_path, model_fields)
                results.extend(image_results)

            return results

        except Exception as e:
            self.console.print(f"[bold red]Error processing bulk images:[/] {e}")
            return []

    def display_results(self, results: List[dict], display_type: str = 'json'):
        """
        Display extraction results
        
        :param results: List of extraction results with input and response
        :param display_type: Display format ('json', 'table')
        """
        try:
            if display_type == 'json':
                # Convert results to a JSON formatted string
                result_json = json.dumps(results, indent=4, ensure_ascii=False)
                
                # Create a Syntax object for syntax highlighting
                syntax = Syntax(result_json, "json", theme="monokai", line_numbers=True)

                # Print the result inside a panel for better presentation
                self.console.print(Panel(syntax, title="Extracted Data", border_style="cyan"))
            
            elif display_type == 'table':
                # Create a rich table for display
                table = Table(title="Extracted Data")
                
                # If results exist, dynamically create columns
                if results:
                    # Get all possible keys from the first result's response
                    response_keys = list(results[0]['response'].keys())
                    
                    # Add columns
                    table.add_column("Input", style="cyan")
                    for key in response_keys:
                        table.add_column(key.replace('_', ' ').title(), style="magenta")
                    
                    # Add rows
                    for item in results:
                        row = [item['input']]
                        row.extend([str(item['response'].get(key, 'N/A')) for key in response_keys])
                        table.add_row(*row)
                
                self.console.print(table)
        
        except Exception as e:
            self.console.print(f"[bold red]Error displaying results:[/] {e}")

    def export_results(self, results: List[dict], output_file: str):
        """
        Export results to various formats
        
        :param results: List of extraction results with input and response
        :param output_file: Output file path
        """
        try:
            # Determine file extension
            _, file_ext = os.path.splitext(output_file)
            file_ext = file_ext.lower()

            # Ensure the directory exists
            os.makedirs(os.path.dirname(output_file) or '.', exist_ok=True)

            # Export based on file type
            if file_ext == '.json':
                # JSON export
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                self.console.print(f"[bold green]Results exported to JSON: {output_file}[/]")
            
            elif file_ext == '.csv':
                # CSV export
                if not results:
                    self.console.print("[bold yellow]No results to export.[/]")
                    return

                # Get all possible keys from the first result's response
                fieldnames = ['input'] + list(results[0]['response'].keys())

                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    
                    # Write header
                    writer.writeheader()
                    
                    # Write rows
                    for item in results:
                        # Prepare row with input and response data
                        row = {'input': item['input']}
                        row.update(item['response'])
                        writer.writerow(row)
                
                self.console.print(f"[bold green]Results exported to CSV: {output_file}[/]")
            
            else:
                self.console.print(f"[bold red]Unsupported file format: {file_ext}. Use .json or .csv[/]")
        
        except PermissionError:
            self.console.print(f"[bold red]Permission denied: Unable to write to {output_file}[/]")
        except OSError as e:
            self.console.print(f"[bold red]OS Error during export: {e}[/]")
        except Exception as e:
            self.console.print(f"[bold red]Unexpected error during export:[/] {e}")

    def __repr__(self):
        return f"DynamicExtractor(model={self.text_model}, vision_model={self.vision_model}, host={self.host})"
    
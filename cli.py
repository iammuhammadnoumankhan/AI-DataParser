#!/usr/bin/env python3
import os
import argparse
from rich.console import Console
from src.extractor import DynamicExtractor

def main():
    parser = argparse.ArgumentParser(description="Dynamic Data Extraction CLI")
    parser.add_argument('--text', help='Text input for extraction')
    parser.add_argument('--image', help='Image path for extraction')
    parser.add_argument('--bulk-text', help='Path to bulk text file (.txt or .csv)')
    parser.add_argument('--bulk-images', help='Path to folder with images')
    parser.add_argument('--display', choices=['json', 'table', 'none'], default='json', 
                        help='Display format for results')
    parser.add_argument('--export', choices=['json', 'csv', 'none'], default='none', 
                        help='Export format for results')
    
    args = parser.parse_args()

    console = Console()
    extractor = DynamicExtractor()

    try:
        # Dynamically define model fields
        model_fields = []
        while True:
            name = input("Enter field name (or press Enter to finish): ")
            if not name:
                if not model_fields:
                    console.print("[bold red]At least one field must be defined![/]")
                    continue
                break
            
            type_options = ['str', 'int', 'float', 'list(str)', 'list(int)', 'list(float)', 'list(bool)', 'bool']
            console.print("Available Types:")
            for idx, t in enumerate(type_options, 1):
                console.print(f"{idx}. {t}")
            
            type_choice = int(input("Choose field type (enter number): ")) - 1
            field_type = type_options[type_choice]
            
            optional_input = input("Is this field optional? (y/n): ").lower()
            while optional_input not in ['y', 'n']:
                console.print("[bold yellow]Invalid input! Please enter 'y' for Yes or 'n' for No.[/]")
                optional_input = input("Is this field optional? (y/n): ").lower()
            optional = optional_input == 'y'
            
            model_fields.append({
                'name': name, 
                'type': field_type, 
                'optional': optional
            })

        results = []
        if args.text:
            results = extractor.process_text(args.text, model_fields)
        elif args.image:
            results = extractor.process_image(args.image, model_fields)
        elif args.bulk_text:
            results = extractor.process_bulk_text(args.bulk_text, model_fields)
        elif args.bulk_images:
            results = extractor.process_bulk_images(args.bulk_images, model_fields)
        else:
            console.print("[bold red]No input specified. Use --help for usage.[/]")
            return

        # Display results
        if results:
            if args.display != 'none':
                extractor.display_results(results, display_type=args.display)

            # Export results
            if args.export != 'none':
                default_json = os.path.join(os.getcwd(), f'extraction_results.{args.export}')
                extractor.export_results(results, default_json)
        else:
            console.print("[bold yellow]No results to export or display.[/]")

    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user.[/]")
    except Exception as e:
        console.print(f"[bold red]An unexpected error occurred: {e}[/]")

if __name__ == "__main__":
    main()
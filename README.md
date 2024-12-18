# Dynamic Data Extractor

## Overview
Dynamic Data Extractor is a flexible CLI tool for extracting structured data from text, images, and bulk files using Ollama's language models.

## Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/dynamic-data-extractor.git
cd dynamic-data-extractor
```

2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure .env
- Modify `.env` file with your Ollama server settings

## Usage

### Basic Usage
```bash
python cli.py --text "Your input text" 
python cli.py --image path/to/image.jpg
python cli.py --bulk-text path/to/data.txt
python cli.py --bulk-images path/to/image/folder
```

### Advanced Options
- `--display`: Choose display format (json/table/none)
- `--export`: Choose export format (json/csv/none)

## Contributing
Please read CONTRIBUTING.md for details on our code of conduct and the process for submitting pull requests.

## License
This project is licensed under the MIT License.
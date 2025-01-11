# Gno Plugin Knowledge Scrapper

A tool for scraping and formatting knowledge from various Gno.land resources to power the [ChatGPT Gno Developer Assistant](https://chatgpt.com/g/g-677dc2d0ba808191b27eb16e06869eec-gno-developer-assistant). This scraper collects and formats content from official documentation and tutorials to enhance the assistant's knowledge base.

## Features

- Extracts content from [Gno by Example](https://gno-by-example.com)
- Scrapes official [Gno documentation](https://github.com/gnolang/gno/tree/master/docs)
- Formats and cleans the extracted content for better readability
- Prepares data for the ChatGPT Gno Developer Assistant plugin

## Purpose

This tool serves as the knowledge base builder for the ChatGPT Gno Developer Assistant. It automatically scrapes and formats:
- Tutorial content from Gno by Example
- Official documentation from the Gno repository
- HTML content for better context preservation

The formatted output is used to train and update the ChatGPT Gno Developer Assistant, ensuring it has access to the latest Gno.land documentation and examples.

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gno-plugin-knowledge-scrapper.git
cd gno-plugin-knowledge-scrapper
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Create a `.env` file from the example:
```bash
cp .env.example .env
```

4. (Optional) Add your GitHub token to `.env` for better rate limits when scraping docs:
```
GITHUB_TOKEN=your_github_token
```

## Usage

Run any of the following commands using Poetry:

```bash
# Extract Gno by Example content
poetry run crawl

# Extract HTML content from Gno by Example
poetry run html

# Format extracted content
poetry run format

# Extract official documentation
poetry run extract
```

The extracted content will be saved in the `gno_plugin_knowledge_scrapper/artifacts` directory, organized by tool.
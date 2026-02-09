"""Initialize knowledge base with Markdown files."""

from pathlib import Path

from src.knowledge.parser import MarkdownParser
from src.knowledge.vector_store import VectorStore
from src.utils.config import config
from src.utils.logger import logger


def initialize_knowledge_base() -> None:
    """Initialize the knowledge base from Markdown files."""
    logger.info("Initializing knowledge base...")

    # Initialize parser and vector store
    parser = MarkdownParser(
        chunk_size=config.chunk_size,
        chunk_overlap=config.chunk_overlap,
    )
    vector_store = VectorStore()

    # Parse all Markdown files
    kb_path = config.knowledge_base_path
    logger.info(f"Parsing Markdown files from: {kb_path}")

    chunks = parser.parse_directory(kb_path)

    if not chunks:
        logger.warning(f"No Markdown files found in {kb_path}")
        logger.info("Creating sample knowledge base files...")

        # Create sample files if none exist
        kb_path.mkdir(parents=True, exist_ok=True)

        sample_files = {
            "Company Policies.md": """# Company Policies

## Working Hours

Standard working hours are from 9:00 AM to 6:00 PM, Monday through Friday.
Employees are expected to be punctual and maintain regular attendance.

## Leave Policy

### Annual Leave
- Full-time employees are entitled to 15 days of paid annual leave per year
- Leave requests must be submitted at least 2 weeks in advance
- Manager approval is required for all leave requests

### Sick Leave
- Employees are entitled to 10 days of paid sick leave per year
- Medical certificate may be required for absences longer than 3 days

### Public Holidays
The company observes all national public holidays.

## Remote Work

Remote work is available with prior manager approval.
Employees must maintain regular communication during remote work periods.
""",
            "Company Procedures & Guidelines.md": """# Company Procedures & Guidelines

## Onboarding Process

New employees should complete the following steps:

1. Review and sign employment contract
2. Complete tax and benefits paperwork
3. Set up company email and system access
4. Complete mandatory training modules
5. Meet with team members and manager

## Expense Reimbursement

### Submitting Expenses
- All expenses must be submitted within 30 days of incurrence
- Receipts are required for expenses over $25
- Use the company expense portal for submissions

### Approved Expenses
- Business travel (transportation, accommodation, meals)
- Office supplies (with prior approval)
- Client entertainment (with manager approval)

## Communication Guidelines

### Email Etiquette
- Use clear and concise subject lines
- Include relevant context in emails
- Response time expectation: within 24 hours

### Meeting Guidelines
- Send agenda at least 24 hours in advance
- Start and end on time
- Take meeting notes and share with attendees
""",
            "Coding Style.md": """# Coding Style Guidelines

## Python Code Style

### General Principles
- Follow PEP 8 conventions
- Use meaningful variable and function names
- Keep functions focused and under 50 lines
- Add docstrings to all public functions

### Type Hints
```python
def process_data(data: List[str]) -> Dict[str, int]:
    \"\"\"Process string data and return counts.\"\"\"
    # implementation
```

### Error Handling
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
```

## JavaScript/TypeScript Code Style

### Naming Conventions
- camelCase for variables and functions
- PascalCase for classes and components
- UPPER_CASE for constants

### Code Organization
- Import order: standard library, third-party, local
- One component per file
- Keep components under 300 lines

## Code Review Guidelines

### Before Submitting
- Run linters and formatters
- Write unit tests for new functionality
- Update documentation
- Ensure no console.log in production code
""",
        }

        for filename, content in sample_files.items():
            file_path = kb_path / filename
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Created sample file: {filename}")

        # Re-parse after creating files
        chunks = parser.parse_directory(kb_path)

    # Add chunks to vector store
    if chunks:
        logger.info(f"Adding {len(chunks)} chunks to vector store...")
        vector_store.add_documents(chunks)
        logger.info("Knowledge base initialized successfully!")
    else:
        logger.error("No chunks to add to knowledge base")


if __name__ == "__main__":
    initialize_knowledge_base()

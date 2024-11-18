# MetaPrompter
Software Requirements Specification

## 1. Overview
MetaPrompter is a Python-based tool that helps developers create focused documentation context (meta-prompts) for AI coding assistants. It manages the workflow of scraping documentation, cleaning it, tracking changes, and generating context-specific documentation extracts. The system uses Jina Reader API to standardize HTML content conversion to markdown, ensuring consistent formatting across different documentation sources.

### 1.1 Documentation Collection
The system scrapes documentation websites from the internet, starting from specified seed URLs. It intelligently traverses documentation structures while respecting domain and path restrictions to collect relevant pages. Using the Jina Reader API, it converts HTML-based documentation into standardized markdown format, preserving code examples and essential formatting while removing navigation elements and other web-specific artifacts. This ensures a consistent base format regardless of the original documentation's presentation style.

### 1.2 Content Processing
After collection, the raw markdown content undergoes a cleaning process using LLM-based transformations. This process:
- Standardizes formatting and structure across different documentation sources
- Removes redundant or navigational content
- Preserves and properly formats code examples and technical content
- Maintains semantic relationships between different sections
- Tracks content changes to avoid reprocessing unchanged documentation
The cleaned content serves as the foundation for generating focused meta-prompts.

### 1.3 Meta-Prompt Generation
Meta-prompts are context-specific documentation extracts tailored for specific development tasks. The generation process:
- Takes a task-specific prompt template as input
- Analyzes the cleaned documentation to identify relevant sections
- Extracts and reorganizes content to match the task context
- Maintains links between related concepts and examples
- Creates focused, self-contained documentation suitable for AI coding assistants
The resulting meta-prompts provide precise, relevant context for specific development tasks while maintaining technical accuracy.

### 1.4 Cost Management
The system implements token-aware operations to manage LLM usage costs effectively:
- Counts tokens before executing LLM operations
- Provides cost estimates before processing stages
- Prompts user confirmation for operations exceeding configured thresholds
- Tracks token usage across different processing stages
- Enables users to monitor and control processing costs
This ensures transparency and control over LLM-related expenses while maintaining processing quality.

## 2. Core Requirements

### 2.1 Project Management
- Projects are the main organizational unit, representing a framework or library documentation set
- Project configuration stored in YAML file
- Source tracking managed in SQLite database
- Projects track:
  - Scraping configuration
  - Source content state
  - Cleaning configuration
  - Meta-prompt definitions

### 2.2 Project Configuration
```yaml
# project.yaml - Project configuration
name: "langchain-tools"
description: "LangChain documentation for tool development"
created: "2024-11-07"
cost_control:
  token_counting: true               # Enable token counting before LLM operations
  prompt_threshold: 1000             # Prompt user if operation exceeds this token count
scrape_job:
  seed_urls:
    - "https://python.langchain.com/docs/modules/agents/tools/"
  spider_options:
    follow_links:                     # Whether to follow links found in pages
    restrict_domain: true             # Restrict to domain of seed URL
    restrict_path: true               # Restrict to path of seed URL
    max_depth: 3                      # How deep to crawl from seed URL
    max_pages: 100                    # maximum page count
    exclusion_patterns:               # URLs matching these patterns will be skipped
      - "*/api/*"
      - "*/changelog/*"
      - "*/legacy/*"
  content_conversion:
    use_jina_reader: true            # Use Jina Reader API for HTML to markdown conversion

cleaning:
  prompt: |
    Clean the following documentation while:
    1. Removing navigation elements
    2. Standardizing formatting
    3. Preserving code examples
    Content: {content}

meta_prompts:
  tool_creation:                      # Will generate meta_prompts/tool_creation.md
    description: "Context for creating custom LangChain tools"
    prompt: |
      Extract relevant documentation sections for:
      Task: Creating custom tools in LangChain
      Requirements:
      - Focus on tool interface
      - Include essential methods
```

### 2.3 Data Models
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam class {
    BackgroundColor #F0F0F0
    BorderColor #808080
    ArrowColor #808080
}

class Project {
    +String name
    +String description
    +Datetime created
    +String path
}

class ScrapeJob {
    +List<String> seed_urls
    +Integer max_pages
    +SpiderOptions spider_options
}

class SpiderOptions {
    +Integer depth
    +Boolean restrict_domain
    +Boolean restrict_path
    +List<String> exclusion_patterns
}

class CleaningConfig {
    +String prompt
}

class MetaPrompt {
    +String name
    +String description
    +String prompt
}

class Page {
    +Integer id
    +String project_id
    +String url
    +String filename
    +String content_hash
}

Project "1" -- "1" ScrapeJob : configures >
ScrapeJob "1" -- "1" SpiderOptions : contains >
Project "1" -- "1" CleaningConfig : configures >
Project "1" -- "n" MetaPrompt : contains >
Project "1" -- "n" Page : tracks >
@enduml
```

### 2.4 Database Schema
```plantuml
@startuml
!define table(x) class x << (T,#FFAAAA) >>
!define primary_key(x) <b>x</b>
!define foreign_key(x) <i>x</i>

skinparam backgroundColor #FFFFFF
skinparam class {
    BackgroundColor #F0F0F0
    BorderColor #808080
}

hide methods
hide stereotypes

table(pages) {
  primary_key(id) INTEGER
  foreign_key(project_id) TEXT
  url TEXT
  filename TEXT
  content_hash TEXT
}
@enduml
```

### 2.5 Project Structure
```
project_dir/
├── project.yaml           # Project configuration
├── project.db            # SQLite database for source tracking
├── scraped/              # Raw scraped markdown files
│   ├── page1.md
│   └── page2.md
├── cleaned/              # LLM-cleaned markdown files
│   ├── page1.md
│   └── page2.md
└── meta_prompts/         # Generated context files
    └── tool_creation.md
```

## 3. Core Workflows

### 3.1 Overall Process Flow
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam state {
    BackgroundColor #F0F0F0
    BorderColor #808080
    ArrowColor #808080
}

[*] --> Scraping
Scraping : Fetch documentation
Scraping : Convert to markdown
Scraping : Track content hashes

Scraping --> Cleaning : New/changed content
Cleaning : LLM-based cleaning
Cleaning : Format standardization

Cleaning --> MetaPromptGen : Generate context
MetaPromptGen : Extract relevant sections
MetaPromptGen : Create focused context
MetaPromptGen --> [*]
@enduml
```

### 3.2 Scraping Workflow
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam sequence {
    LifeLineBorderColor #808080
    ParticipantBorderColor #808080
    ParticipantBackgroundColor #F0F0F0
}

participant "CLI" as CLI
participant "Project Manager" as PM
participant "Scraper" as SC
participant "Jina Reader" as JR
participant "Source Tracker" as ST
database "SQLite" as DB
database "Files" as FS

CLI -> PM: Run scrape
PM -> SC: Configure spider
SC -> JR: Convert HTML to markdown
JR -> SC: Return standardized content
SC -> FS: Write to scraped/
SC -> ST: Update content hashes
ST -> DB: Update page records
PM -> CLI: Report completion
@enduml
```

### 3.3 Content Change Detection
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam sequence {
    LifeLineBorderColor #808080
    ParticipantBorderColor #808080
    ParticipantBackgroundColor #F0F0F0
}

participant "Project Manager" as PM
participant "Source Tracker" as ST
database "SQLite" as DB

PM -> ST: Check for updates
ST -> DB: Get stored hashes
ST -> ST: Compare with file hashes
ST --> PM: Return changed files
@enduml
```

### 3.4 Component Structure
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam component {
    BackgroundColor #F0F0F0
    BorderColor #808080
}

package "MetaPrompter" {
    [CLI] as cli
    [Project Manager] as pm
    [Scraper] as scraper
    [Source Tracker] as tracker
    [Cleaner] as cleaner
    [Generator] as generator
    database "SQLite DB" as db
    folder "File System" as fs
    
    cli --> pm
    pm --> scraper
    pm --> tracker
    pm --> cleaner
    pm --> generator
    tracker --> db
    scraper --> fs
    cleaner --> fs
    generator --> fs
}

[LLM API] as llm
cleaner --> llm
generator --> llm
@enduml
```

## 4. Command Line Interface

### 4.1 Commands
```bash
metaprompter init <n>      # Create new project
metaprompter scrape           # Run scrape job
metaprompter status          # Show file status
metaprompter clean           # Run cleaning job
metaprompter generate <n> # Generate meta-prompt
metaprompter tokens          # Show token count for next operation
```

### 4.2 Command Flow
```plantuml
@startuml
skinparam backgroundColor #FFFFFF
skinparam state {
    BackgroundColor #F0F0F0
    BorderColor #808080
    ArrowColor #808080
}

[*] --> Init
Init : Create project.yaml
Init : Initialize database

state "Project Setup" as setup {
    Init --> Scrape
}

state "Content Processing" as processing {
    Scrape --> Clean : Changed content
    Clean --> Generate : Clean content
}

Generate --> [*]

note right of setup : Project initialization phase
note right of processing : Content processing phase
@enduml
```

## 5. Error Handling
- Basic error logging to file
- Clear error messages for user
- Token count warnings and prompts
- Graceful handling of:
  - Network errors during scraping
  - LLM API errors
  - File system errors
  - Database errors

## 6. Performance Considerations
- Efficient hash comparison
- Process only changed files
- Simple database queries
- Standard logging instead of database history

## 7. Future Extensions
- Web UI for interactive refinement
- Template system for cleaning prompts
- Multiple framework versions
- Direct AI assistant integration
- Alternative HTML to markdown converters as fallback options
- Quality validation system for LLM outputs
- Automated meta-prompt effectiveness scoring
- Content accuracy verification tools
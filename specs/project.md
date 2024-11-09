# MetaPrompter
Software Requirements Specification

## 1. Overview
MetaPrompter is a Python-based tool that helps developers create focused documentation context (meta-prompts) for AI coding assistants. It manages the workflow of scraping documentation, cleaning it, tracking changes, and generating context-specific documentation extracts.

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
participant "Source Tracker" as ST
database "SQLite" as DB
database "Files" as FS

CLI -> PM: Run scrape
PM -> SC: Configure spider
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
metaprompter init <name>      # Create new project
metaprompter scrape           # Run scrape job
metaprompter status          # Show file status
metaprompter clean           # Run cleaning job
metaprompter generate <name> # Generate meta-prompt
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

Would you like me to:
1. Add more detailed workflow diagrams?
2. Expand any section further?
3. Add more implementation details?
4. Include additional error scenarios?
5. Detail specific components further?
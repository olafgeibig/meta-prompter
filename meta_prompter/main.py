from meta_prompter.parallel_scraper import ParallelScraper
import logging


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create scraper instance
    scraper = ParallelScraper()

    # URL to scrape
    urls = ["https://docs.crewai.com/concepts/agents"]

    try:
        # Perform scraping
        scraper.scrape_urls(urls)
        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}")

if __name__ == "__main__":
    main()

from meta_prompter.parallel_scraper import ParallelScraper
import logging
from meta_prompter.custom_types import ScrapingJob


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create scraper instance
    scraper = ParallelScraper()

    job = ScrapingJob(
        name="crewAI",
        seed_urls = ["https://docs.crewai.com/concepts/agents"],
        max_pages=5
    )

    try:
        # Perform scraping
        scraper.run_spider(job)
        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}")

if __name__ == "__main__":
    main()

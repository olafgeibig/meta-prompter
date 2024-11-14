from meta_prompter.parallel_scraper import ParallelScraper
import logging
from meta_prompter.custom_types import ScrapeJob


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create scraper instance
    scraper = ParallelScraper()

    job = ScrapeJob(
        name="crewAI",
        seed_urls=["https://docs.crewai.com/concepts/agents"],
        follow_links=True,
        domain_restricted=True,
        path_restricted=True,
        max_pages=5,
        max_depth=None,
        exclusion_patterns=[],
        pages=set(),
        url_depths={}
    )

    try:
        # Perform scraping
        scraper.run(job)
        logging.info("Scraping completed successfully")
    except Exception as e:
        logging.error(f"Scraping failed: {str(e)}")

if __name__ == "__main__":
    main()

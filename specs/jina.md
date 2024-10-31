Endpoint: https://r.jina.ai/
Purpose: retrieve/parse content from  URL in a format optimized for downstream tasks like LLMs and other applications
Best for: extracting structured content from web pages, suitable for generative models and search applications
Method: POST
Authorization: HTTPBearer
Headers:
- **Authorization**: Bearer 
- **Content-Type**: application/json
- **Accept**: application/json
- **X-Timeout** (optional): Specifies the maximum time (in seconds) to wait for the webpage to load
- **X-Target-Selector** (optional): CSS selectors to focus on specific elements within the page
- **X-Wait-For-Selector** (optional): CSS selectors to wait for specific elements before returning
- **X-Remove-Selector** (optional): CSS selectors to exclude certain parts of the page (e.g., headers, footers)
- **X-With-Links-Summary** (optional): `true` to gather all links at the end of the response
- **X-With-Images-Summary** (optional): `true` to gather all images at the end of the response
- **X-With-Generated-Alt** (optional): `true` to add alt text to images lacking captions
- **X-No-Cache** (optional): `true` to bypass cache for fresh retrieval
- **X-With-Iframe** (optional): `true` to include iframe content in the response

Request body schema: {"application/json":{"url":{"type":"string","required":true},"options":{"type":"string","default":"Default","options":["Default","Markdown","HTML","Text","Screenshot","Pageshot"]}}}
Example cURL request: ```curl -X POST 'https://r.jina.ai/' -H "Accept: application/json" -H "Authorization: Bearer ..." -H "Content-Type: application/json" -H "X-No-Cache: true" -H "X-Remove-Selector: header,.class,#id" -H "X-Target-Selector: body,.class,#id" -H "X-Timeout: 10" -H "X-Wait-For-Selector: body,.class,#id" -H "X-With-Generated-Alt: true" -H "X-With-Iframe: true" -H "X-With-Images-Summary: true" -H "X-With-Links-Summary: true" -d '{"url":"https://jina.ai"}'```
Example response: {"code":200,"status":20000,"data":{"title":"Jina AI - Your Search Foundation, Supercharged.","description":"Best-in-class embeddings, rerankers, LLM-reader, web scraper, classifiers. The best search AI for multilingual and multimodal data.","url":"https://jina.ai/","content":"Jina AI - Your Search Foundation, Supercharged.\n===============\n","images":{"Image 1":"https://jina.ai/Jina%20-%20Dark.svg"},"links":{"Newsroom":"https://jina.ai/#newsroom","Contact sales":"https://jina.ai/contact-sales","Commercial License":"https://jina.ai/COMMERCIAL-LICENSE-TERMS.pdf","Security":"https://jina.ai/legal/#security","Terms & Conditions":"https://jina.ai/legal/#terms-and-conditions","Privacy":"https://jina.ai/legal/#privacy-policy"},"usage":{"tokens
Pay attention to the response format of the reader API, the actual content of the page will be available in `response["data"]["content"]`, and links / images (if using "X-With-Links-Summary: true" or "X-With-Images-Summary: true") will be available in `response["data"]["links"]` and `response["data"]["images"]`.
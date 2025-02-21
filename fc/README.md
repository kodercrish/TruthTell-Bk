# Enhanced Factcheck with a pipeline for news data

* Using Serper search inspired from Loki's web search implementation
* Fact checking with different LLM layers powered with Gemini to use the web search tool to get sources of data, and perform fact checking, powered with structuring using Gemini
* Getting news from NewsAPI, scraping the URLs using newspaper library
* Performing fact check on the structured news obtained
* Pipeline using glassflow to send the fact checked data via the pipeline, from the backend to frontend
* This, powered with websockets, allows for live streaming of data from backend



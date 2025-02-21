from concurrent.futures import ThreadPoolExecutor
import json
import requests
import dotenv
import os
import re
import bs4

dotenv.load_dotenv()

################################################################################################
import requests
import backoff
import time
import bs4
import asyncio
from httpx import AsyncHTTPTransport
from httpx._client import AsyncClient


USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:65.0) Gecko/20100101 Firefox/65.0"
# mobile user-agent
MOBILE_USER_AGENT = "Mozilla/5.0 (Linux; Android 7.0; SM-G930V Build/NRD90M) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.125 Mobile Safari/537.36"
headers = {"User-Agent": USER_AGENT}


def is_tag_visible(element: bs4.element) -> bool:
    """Determines if an HTML element is visible.

    Args:
        element: A BeautifulSoup element to check the visibility of.
    returns:
        Whether the element is visible.
    """
    if element.parent.name in [
        "style",
        "script",
        "head",
        "title",
        "meta",
        "[document]",
    ] or isinstance(element, bs4.element.Comment):
        return False
    return True


transport = AsyncHTTPTransport(retries=3)


async def httpx_get(url: str, headers: dict):
    try:
        async with AsyncClient(transport=transport) as client:
            response = await client.get(url, headers=headers, timeout=3)
            response = response if response.status_code == 200 else None
            if not response:
                return False, None
            else:
                return True, response
    except Exception as e:  # noqa: F841
        return False, None


async def httpx_bind_key(url: str, headers: dict, key: str = ""):
    flag, response = await httpx_get(url, headers)
    return flag, response, url, key


def crawl_web(query_url_dict: dict):
    tasks = list()
    for query, urls in query_url_dict.items():
        for url in urls:
            task = httpx_bind_key(url=url, headers=headers, key=query)
            tasks.append(task)
    asyncio.set_event_loop(asyncio.SelectorEventLoop())
    loop = asyncio.get_event_loop()
    responses = loop.run_until_complete(asyncio.gather(*tasks))
    return responses


# @backoff.on_exception(backoff.expo, (requests.exceptions.RequestException, requests.exceptions.Timeout), max_tries=1,max_time=3)
def common_web_request(url: str, query: str = None, timeout: int = 3):
    resp = requests.get(url, headers=headers, timeout=timeout)
    if query:
        return resp, query
    else:
        return resp


def parse_response(response: requests.Response, url: str, query: str = None):
    html_content = response.text
    url = url
    try:
        soup = bs4.BeautifulSoup(html_content, "html.parser")
        texts = soup.findAll(text=True)
        # Filter out invisible text from the page.
        visible_text = filter(is_tag_visible, texts)
    except Exception as _:  # noqa: F841
        return None, url, query

    # Returns all the text concatenated as a string.
    web_text = " ".join(t.strip() for t in visible_text).strip()
    # Clean up spacing.
    web_text = " ".join(web_text.split())
    return web_text, url, query


def scrape_url(url: str, timeout: float = 3):
    """Scrapes a URL for all text information.

    Args:
        url: URL of webpage to scrape.
        timeout: Timeout of the requests call.
    Returns:
        web_text: The visible text of the scraped URL.
        url: URL input.
    """
    # Scrape the URL
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.RequestException as _:  # noqa: F841
        return None, url

    # Extract out all text from the tags
    try:
        soup = bs4.BeautifulSoup(response.text, "html.parser")
        texts = soup.findAll(text=True)
        # Filter out invisible text from the page.
        visible_text = filter(is_tag_visible, texts)
    except Exception as _:  # noqa: F841
        return None, url

    # Returns all the text concatenated as a string.
    web_text = " ".join(t.strip() for t in visible_text).strip()
    # Clean up spacing.
    web_text = " ".join(web_text.split())
    return web_text, url


def crawl_google_web(response, top_k: int = 10):
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    # with open("text%d.html"%time.time(), 'w') as fw:
    #     fw.write(response.text)
    valid_node_list = list()
    for node in soup.find_all("a", {"href": True}):
        if node.findChildren("h3"):
            valid_node_list.append(node)
    result_urls = list()
    for node in valid_node_list:
        result_urls.append(node.get("href"))
    # result_urls = [link.get("href") for link in node if link.get("href")]
    return result_urls[:top_k]

################################################################################################

import os
import logging
from flask import g
from logging.handlers import TimedRotatingFileHandler

class CustomLogger:
    def __init__(self, name: str, loglevel=logging.INFO):
        self.logger = logging.getLogger("FactCheck")
        self.logger.setLevel(loglevel)
        
        if not os.path.exists("./log"):
            os.makedirs("./log")
            
        env = os.environ.get("env", "dev")
        fh = TimedRotatingFileHandler(filename="./log/factcheck_{}.log".format(env), when="D", encoding="utf-8")
        fh.setLevel(loglevel)
        
        if not self.logger.handlers:
            formatter = logging.Formatter("[%(levelname)s]%(asctime)s %(filename)s:%(lineno)d: %(message)s")
            fh.setFormatter(formatter)
            # Only add the file handler, removing the console handler
            self.logger.addHandler(fh)

    def getlog(self):
        return self.logger

#########################################################################################################################################################################

logger = CustomLogger(__name__).getlog()


class SerperEvidenceRetriever:
    def __init__(self, api_key: str):
        """Initialize the SerperEvidenceRetrieve class"""
        self.lang = "en"
        self.serper_key = api_key
        

    def retrieve_evidence(self, claim_queries_dict, top_k: int = 3, snippet_extend_flag: bool = True):
        """Retrieve evidences for the given claims

        Args:
            claim_queries_dict (dict): a dictionary of claims and their corresponding queries.
            top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
            snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.

        Returns:
            dict: a dictionary of claims and their corresponding evidences.
        """
        logger.info("Collecting evidences ...")
        query_list = [y for x in claim_queries_dict.items() for y in x[1]]
        evidence_list = self._retrieve_evidence_4_all_claim(
            query_list=query_list, top_k=top_k, snippet_extend_flag=snippet_extend_flag
        )

        i = 0
        claim_evidence_dict = {}
        for claim, queries in claim_queries_dict.items():
            evidences_per_query_L = evidence_list[i : i + len(queries)]
            claim_evidence_dict[claim] = [e for evidences in evidences_per_query_L for e in evidences]
            i += len(queries)
        assert i == len(evidence_list)
        logger.info("Collect evidences done!")

        return claim_evidence_dict

    def _retrieve_evidence_4_all_claim(
        self, query_list: list[str], top_k: int = 3, snippet_extend_flag: bool = True
    ) -> list[list[str]]:
        """Retrieve evidences for the given queries

        Args:
            query_list (list[str]): a list of queries to retrieve evidences for.
            top_k (int, optional): the number of top relevant results to retrieve. Defaults to 3.
            snippet_extend_flag (bool, optional): whether to extend the snippet. Defaults to True.

        Returns:
            list[list[]]: a list of [a list of evidences for each given query].
        """

        # init the evidence list with None
        evidences = [[] for _ in query_list]

        # get the response from serper
        serper_responses = []
        for i in range(0, len(query_list), 100):
            batch_query_list = query_list[i : i + 100]
            batch_response = self._request_serper_api(batch_query_list)
            if batch_response is None:
                logger.error("Serper API request error!")
                return evidences
            else:
                serper_responses += batch_response.json()

        # get the responses for queries with an answer box
        query_url_dict = {}
        url_to_date = {}  # TODO: decide whether to use date
        _snippet_to_check = []
        for i, (query, response) in enumerate(zip(query_list, serper_responses)):
            if query != response.get("searchParameters").get("q"):
                logger.error("Serper change query from {} TO {}".format(query, response.get("searchParameters").get("q")))

            # TODO: provide the link for the answer box
            if "answerBox" in response:
                if "answer" in response["answerBox"]:
                    evidences[i] = [
                        {
                            "text": f"{query}\nAnswer: {response['answerBox']['answer']}",
                            "url": "Google Answer Box",
                        }
                    ]
                else:
                    evidences[i] = [
                        {
                            "text": f"{query}\nAnswer: {response['answerBox']['snippet']}",
                            "url": "Google Answer Box",
                        }
                    ]
            # TODO: currently --- if there is google answer box, we only got 1 evidence, otherwise, we got multiple, this will deminish the value of the google answer.
            else:
                topk_results = response.get("organic", [])[:top_k]  # Choose top 5 response

                if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
                    evidences[i] += [
                        {"text": re.sub(r"\n+", "\n", _result["snippet"]), "url": _result["link"]} for _result in topk_results
                    ]

                # Save date for each url
                url_to_date.update({_result.get("link"): _result.get("date") for _result in topk_results})
                # Save query-url pair, 1 query may have multiple urls
                query_url_dict.update({query: [_result.get("link") for _result in topk_results]})
                _snippet_to_check += [_result["snippet"] if "snippet" in _result else "" for _result in topk_results]

        # return if there is no snippet to check or snippet_extend_flag is False
        if (len(_snippet_to_check) == 0) or (not snippet_extend_flag):
            return evidences

        # crawl web for queries without answer box
        responses = crawl_web(query_url_dict)
        # Get extended snippets based on the snippet from serper
        flag_to_check = [_item[0] for _item in responses]
        response_to_check = [_item[1] for _item in responses]
        url_to_check = [_item[2] for _item in responses]
        query_to_check = [_item[3] for _item in responses]

        def bs4_parse_text(response, snippet, flag):
            """Parse the text from the response and extend the snippet

            Args:
                response (web response): the response from the web
                snippet (str): the snippet to extend from the search result
                flag (bool): flag to extend the snippet

            Returns:
                _type_: _description_
            """
            if flag and ".pdf" not in str(response.url):
                soup = bs4.BeautifulSoup(response.text, "html.parser")
                text = soup.get_text()
                # Search for the snippet in text
                snippet_start = text.find(snippet[:-10])
                if snippet_start == -1:
                    return snippet
                else:
                    pre_context_range = 0  # Number of characters around the snippet to display
                    post_context_range = 500  # Number of characters around the snippet to display
                    start = max(0, snippet_start - pre_context_range)
                    end = snippet_start + len(snippet) + post_context_range
                    return text[start:end] + " ..."
            else:
                return snippet

        # Question: if os.cpu_count() cause problems when running in parallel?
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            _extended_snippet = list(
                executor.map(
                    lambda _r, _s, _f: bs4_parse_text(_r, _s, _f),
                    response_to_check,
                    _snippet_to_check,
                    flag_to_check,
                )
            )

        # merge the snippets by query
        query_snippet_url_dict = {}
        for _query, _url, _snippet in zip(query_to_check, url_to_check, _extended_snippet):
            _snippet_url_list = query_snippet_url_dict.get(_query, [])
            _snippet_url_list.append((_snippet, _url))
            query_snippet_url_dict[_query] = _snippet_url_list

        # extend the evidence list for each query
        for _query in query_snippet_url_dict.keys():
            _query_index = query_list.index(_query)
            _snippet_url_list = query_snippet_url_dict[_query]
            evidences[_query_index] += [
                {"text": re.sub(r"\n+", "\n", snippet), "url": _url} for snippet, _url in _snippet_url_list
            ]

        return evidences

    def _request_serper_api(self, questions):
        """Request the serper api

        Args:
            questions (list): a list of questions to request the serper api.

        Returns:
            web response: the response from the serper api
        """
        url = "https://google.serper.dev/search"

        headers = {
            "X-API-KEY": self.serper_key,
            "Content-Type": "application/json",
        }

        questions_data = [{"q": question, "autocorrect": False} for question in questions]
        payload = json.dumps(questions_data)
        response = None
        response = requests.request("POST", url, headers=headers, data=payload)

        if response.status_code == 200:
            return response
        elif response.status_code == 403:
            raise Exception("Failed to authenticate. Check your API key.")
        else:
            raise Exception(f"Error occurred: {response.text}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--serper_api_key", type=str, help="API key for serper")
    args = parser.parse_args()

    api_config = {"SERPER_API_KEY": args.serper_api_key}
    retriever = SerperEvidenceRetriever(api_config)

    result = retriever._request_serper_api(["Apple", "IBM"])
    #print(result.json())

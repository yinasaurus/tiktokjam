# Marketplace Search Research

Team: **kpopy demon hunter**

Research scope: Taobao, Lazada, Shopee, and Amazon.

Goal: learn what mature shopping platforms do for shopper search, then copy the
useful parts into our offline TechJam agent without adding paid APIs or network
dependency.

## 1. Simple Summary

Modern shopping search is not just keyword matching. The strongest platforms
combine:

| Step | Plain meaning |
|---|---|
| Intent understanding | Work out what the shopper is really asking for. |
| Clarification | Ask a follow-up question when the request is too vague. |
| Hybrid retrieval | Pull candidates from multiple routes, not one search method. |
| Reranking | Sort the final products so the best answer is near the top. |
| Personalization | Use user history when reliable and available. |
| Fallbacks | Keep returning useful results even if one route fails. |

Our TechJam version is the small offline version of that pattern.

## 2. Platform Comparison

| Platform | What they appear to do | What we can use | Status in our repo |
|---|---|---|---|
| Taobao | Alibaba connected Qwen to Taobao, so users can browse, compare, order, and manage delivery through conversation. Taobao Wenwen-style assistants also suggest follow-up questions such as budget or style. | Use conversation as the interface. Ask better questions. Keep session state. | Implemented through `ask_attribute` and per-session memory. |
| Lazada | LazzieChat / AI Lazzie turns shopping questions into product suggestions and product links. Lazada also reports GenAI features for product info, smart reviews, translation, and recommendations. | Keep answers simple and product-grounded. Use product metadata and shopper preferences without needing a paid API. | Implemented through product metadata ranking and offline responses. |
| Shopee | Public product-search detail is thinner, but Shopee has search/recommendation teams and published/linked work around recommendation, item graphs, embeddings, and conversational discovery through ChatGPT integrations. | Graph-scale personalization is too heavy for us, but catalog-derived similarity and lightweight embeddings are reasonable research paths. | Research only: dense/Model2Vec hooks exist but are not submitted by default. |
| Amazon | Rufus/Alexa for Shopping uses conversation, product catalog, reviews, Q&A, shopping activity, and retrieval-augmented generation. Amazon Science also describes query parsing, product-aware autocomplete, BM25/full-text search, embeddings, and retrieval/ranking funnels. | This is closest to our challenge: parse attributes, retrieve from several routes, then rank the Top 10. | Implemented as category + exact + lexical + fallback ranking; BM25/LTR remain research paths. |

## 3. Lessons For Our Agent

| Lesson | Why it matters | Our implementation |
|---|---|---|
| Ask while recommending | A question should not stop us from returning candidates. | Always return Top 10 and a valid `ask_attribute`. |
| Track state | Shoppers reveal constraints over time. | `agent/state.py` stores session memory and intent changes. |
| Handle overrides | Real shoppers change their mind. | New override constraints replace older conflicting intent. |
| Use hybrid retrieval | One search route misses too much. | Category, exact constraints, lexical/token scoring, popularity fallback, optional dense/LTR research. |
| Avoid paid dependency | Final scoring should be reproducible. | Default path has no hosted LLM, no paid API, zero tokens. |
| Evaluate honestly | Production systems compare methods. | Keep ablation tables and submit only the best measured method. |

## 4. What We Should Not Copy Now

| Competitor idea | Why not now |
|---|---|
| Full LLM training | Out of scope and too slow. |
| Paid LLM reranking | User requirement says no paid API calls. |
| Huge user-history personalization | Public/private sessions are isolated and the given profile has weak signal. |
| Heavy vector database | The challenge scope expects light in-memory execution. |
| Multimodal shopping | Official track is text-only. |
| Checkout/order automation | Judges score backend recommendations, not real purchase flow. |

## 5. Sources

| Platform | Source |
|---|---|
| Taobao / Qwen | https://www.alibabagroup.com/en-US/document-1991231293551017984 |
| Alibaba recommendation architecture | https://www.alibabacloud.com/blog/595909 |
| Taobao Wenwen coverage | https://www.yicaiglobal.com/news/alibabas-taobao-tests-chatgpt-like-shopping-assistant-taobao-wenwen |
| Lazada GenAI features | https://www.prnewswire.com/apac/news-releases/lazada-announces-suite-of-genai-features-to-transform-shopping-and-seller-experiences-in-southeast-asia-302290849.html |
| LazzieChat announcement | https://news.microsoft.com/source/asia/2023/05/30/lazada-unveils-lazziechat-the-first-ecommerce-ai-chatbot-of-its-kind-in-se-asia/ |
| Shopee app in ChatGPT | https://www.sea.com/news/406 |
| Shopee LightSAGE paper | https://arxiv.org/abs/2310.19394 |
| Amazon Rufus technology | https://www.amazon.science/blog/the-technology-behind-amazons-genai-powered-shopping-assistant-rufus |
| Amazon Rufus personalization | https://www.aboutamazon.com/news/retail/amazon-rufus-ai-assistant-personalized-shopping-features |
| Amazon implicit query parsing | https://www.amazon.science/publications/implicit-query-parsing-for-product-search |
| Amazon ProductRAG autocomplete | https://www.amazon.science/publications/a-product-aware-query-auto-completion-framework-for-e-commerce-search-via-retrieval-augmented-generation-method |
| Amazon learning-to-rank/retrieve | https://www.amazon.science/blog/from-structured-search-to-learning-to-rank-and-retrieve |
| Amazon synthetic query generation | https://www.amazon.science/publications/improving-search-for-new-product-categories-via-synthetic-query-generation-strategies |

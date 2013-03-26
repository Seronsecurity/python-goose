# -*- coding: utf-8 -*-
"""\
This is a python port of "Goose" orignialy licensed to Gravity.com
under one or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.

Python port was written by Xavier Grangier for Recrutae

Gravity.com licenses this file
to you under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import os
import glob
from copy import deepcopy
from goose.article import Article
from goose.utils import URLHelper
from goose.extractors import StandardContentExtractor
from goose.cleaners import StandardDocumentCleaner
from goose.outputformatters import StandardOutputFormatter
from goose.parsers import Parser
from goose.images.extractors import UpgradedImageIExtractor
from goose.network import HtmlFetcher


class CrawlCandidate(object):

    def __init__(self, config, url, rawHTML):
        self.config = config
        self.url = url
        self.rawHTML = rawHTML


class Crawler(object):

    def __init__(self, config):
        self.config = config
        self.logPrefix = "crawler:"

    def crawl(self, crawlCandidate):
        article = Article()

        parseCandidate = URLHelper.getCleanedUrl(crawlCandidate.url)
        rawHtml = self.getHTML(crawlCandidate, parseCandidate)

        if rawHtml is None:
            return article

        doc = self.getDocument(parseCandidate.url, rawHtml)

        extractor = self.getExtractor()
        docCleaner = self.getDocCleaner()
        outputFormatter = self.getOutputFormatter()

        # article
        article.final_url = parseCandidate.url
        article.link_hash = parseCandidate.link_hash
        article.raw_html = rawHtml
        article.doc = doc
        article.raw_doc = deepcopy(doc)
        article.title = extractor.getTitle(article)
        # TODO
        # article.publish_date = config.publishDateExtractor.extract(doc)
        # article.additional_data = config.get_additionaldata_extractor.extract(doc)
        article.meta_lang = extractor.getMetaLang(article)
        article.meta_favicon = extractor.getMetaFavicon(article)
        article.meta_description = extractor.getMetaDescription(article)
        article.meta_keywords = extractor.getMetaKeywords(article)
        article.canonical_link = extractor.getCanonicalLink(article)
        article.domain = extractor.getDomain(article.final_url)
        article.tags = extractor.extractTags(article)
        # # before we do any calcs on the body itself let's clean up the document
        article.doc = docCleaner.clean(article)

        # big stuff
        article.top_node = extractor.calculateBestNodeBasedOnClustering(article)
        if article.top_node is not None:
            # TODO
            # movies and images
            # article.movies = extractor.extractVideos(article.top_node)
            if self.config.enable_image_fetching:
                imageExtractor = self.getImageExtractor(article)
                article.top_image = imageExtractor.getBestImage(article.raw_doc, article.top_node)

            article.top_node = extractor.postExtractionCleanup(article.top_node)
            article.cleaned_text = outputFormatter.getFormattedText(article)

        # cleanup tmp file
        self.releaseResources(article)

        return article

    def getHTML(self, crawlCandidate, parsingCandidate):
        if crawlCandidate.rawHTML:
            return crawlCandidate.rawHTML
        else:
            # fetch HTML
            html = HtmlFetcher().getHtml(self.config, parsingCandidate.url)
            return html

    def getImageExtractor(self, article):
        httpClient = None
        return UpgradedImageIExtractor(httpClient, article, self.config)

    def getOutputFormatter(self):
        return StandardOutputFormatter(self.config)

    def getDocCleaner(self):
        return StandardDocumentCleaner()

    def getDocument(self, url, rawHtml):
        doc = Parser.fromstring(rawHtml)
        return doc

    def getExtractor(self):
        return StandardContentExtractor(self.config)

    def releaseResources(self, article):
        path = '%s/%s_*' % (self.config.local_storage_path, article.link_hash)
        for fname in glob.glob(path):
            try:
                os.remove(fname)
            except OSError:
                # TODO better log handeling
                pass
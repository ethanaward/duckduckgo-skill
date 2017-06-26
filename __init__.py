# Copyright 2016 Mycroft AI, Inc.
#
# This file is part of Mycroft Core.
#
# Mycroft Core is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Mycroft Core is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Mycroft Core.  If not, see <http://www.gnu.org/licenses/>.


from StringIO import StringIO

import re
import duckduckgo
from os.path import dirname, join
from requests import HTTPError

from mycroft.api import Api
from mycroft.messagebus.message import Message
from mycroft.skills.core import MycroftSkill
from mycroft.util.log import getLogger
from mycroft.util.parse import normalize

LOG = getLogger(__name__)


class EnglishQuestionParser(object):
    """
    Poor-man's english question parser. Not even close to conclusive, but
    appears to construct some decent w|a queries and responses.
    """

    def __init__(self):
        self.regexes = [
            re.compile(
                ".*(?P<QuestionWord>who|what|when|where|why|which|whose) "
                "(?P<Query1>.*) (?P<QuestionVerb>is|are|was|were) "
                "(?P<Query2>.*)"),
            re.compile(
                ".*(?P<QuestionWord>who|what|when|where|why|which|how) "
                "(?P<QuestionVerb>\w+) (?P<Query>.*)")
        ]

    def _normalize(self, groupdict):
        if 'Query' in groupdict:
            return groupdict
        elif 'Query1' and 'Query2' in groupdict:
            return {
                'QuestionWord': groupdict.get('QuestionWord'),
                'QuestionVerb': groupdict.get('QuestionVerb'),
                'Query': ' '.join([groupdict.get('Query1'), groupdict.get(
                    'Query2')])
            }

    def parse(self, utterance):
        for regex in self.regexes:
            match = regex.match(utterance)
            if match:
                return self._normalize(match.groupdict())
        return None


class DuckDuckGoSkill(MycroftSkill):

    def __init__(self):
        MycroftSkill.__init__(self, name="DuckDuckGoSkill")
        self.question_parser = EnglishQuestionParser()

    def initialize(self):
        self.emitter.on('intent_failure', self.handle_fallback)

    # TODO: Localization
    def handle_fallback(self, message):
        utt = message.data.get('utterance')
        LOG.debug("DuckDuckGo fallback attempt: " + utt)
        lang = message.data.get('lang')
        if not lang:
            lang = "en-us"

        utterance = normalize(utt, lang)
        parsed_question = self.question_parser.parse(utterance)

        query = utterance
        if parsed_question:
            # Try to store pieces of utterance (None if not parsed_question)
            utt_word = parsed_question.get('QuestionWord')
            utt_verb = parsed_question.get('QuestionVerb')
            utt_query = parsed_question.get('Query')
            if utt_verb == "'s":
                utt_verb = 'is'
                parsed_question['QuestionVerb'] = 'is'
            query = "%s %s %s" % (utt_word, utt_verb, utt_query)
            phrase = "know %s %s %s" % (utt_word, utt_query, utt_verb)
            LOG.debug("Falling back to DuckDuckGo: " + query)
        else:
            # This utterance doesn't look like a question, don't waste
            # time with DuckDuckgo.

            # TODO: Log missed intent
            LOG.debug("Unknown intent: " + utterance)
            return

        resp = duckduckgo.get_zci(utt_query, web_fallback=False)
        print resp.split("(")[0]
        self.speak(resp.split("(")[0])


    def stop(self):
        pass


def create_skill():
    return DuckDuckGoSkill()

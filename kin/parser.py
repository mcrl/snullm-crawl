from bs4 import BeautifulSoup
import json
from io import StringIO
import re
import traceback


def remove_duplicate_whitespace(text):
    return re.sub(r"\s+", " ", text).strip()


def clean_nbsp(text):
    return text.replace("\xa0", " ").strip()


def clean_routine(text):
    return remove_duplicate_whitespace(clean_nbsp(text))


def remove_comment(text):
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)


def build_text(tag, buf=None):
    if buf is None:
        buf = StringIO()
    if tag is None:
        return ""
    for child in tag.children:
        if child.name is None:
            line = remove_duplicate_whitespace(child.string)
            buf.write(line.strip())
            buf.write("\n")
        else:
            build_text(child, buf)
    return buf.getvalue().strip()


def process_vote_tag(tag):
    if not tag:
        return 0
    msg = tag.text.strip()
    try:
        return int(msg)
    except ValueError:
        return 0


def find_answer_text_tag(tag):
    candidates = ["div.se-module", "div.answerDetail"]
    for candidate in candidates:
        text_tag = tag.select_one(candidate)
        if text_tag:
            return text_tag
    return None


def process_answer(tag):
    # answer badges
    entry = {}
    selector = "div.profile_card._profileCardArea > a > div.card_info > div.profile_info > div.badge_area"
    tags = tag.select(selector)
    if tags:
        badge_text = tags[0].text.strip()
        badges = badge_text.split("\n")
    else:
        badges = []
    entry["badges"] = badges

    text_tag = find_answer_text_tag(tag)
    text = build_text(text_tag)
    entry["text"] = text

    # upvote, downvote
    selector = "button.endButton--up > span.countWrap"
    vote_tag = tag.select_one(selector)
    entry["upvote"] = process_vote_tag(vote_tag)

    selector = "button.endButton--down > span.countWrap"
    vote_tag = tag.select_one(selector)
    entry["downvote"] = process_vote_tag(vote_tag)

    # adopted
    selector = "ul.infoList > li > p.description"
    tag = tag.select_one(selector)
    if not tag:
        entry["adopted"] = {"user": False, "kin": False}
    else:
        msg = tag.text.strip()
        entry["adopted"] = {"user": "질문자" in msg, "kin": "지식인" in msg}
    return entry


def parse_html(html, document):
    # clean html
    try:
        html = remove_comment(html)
        soup = BeautifulSoup(html, "html.parser")

        # badge area
        selector = "#content > div.endContentLeft._endContentLeft > div.contentArea._contentWrap > div.adoptBadgeArea"
        tags = soup.select(selector)
        badges = [tag.text.strip() for tag in tags]

        # title selector
        selector = "#content > div.endContentLeft._endContentLeft > div.contentArea._contentWrap > div.endTitleSection"
        tag = soup.select_one(selector)
        title = build_text(tag)
        title = clean_routine(title)

        # question area
        selector = "#content > div.endContentLeft._endContentLeft > div.contentArea._contentWrap > div.questionDetail"
        tag = soup.select_one(selector)
        question = build_text(tag)
        question = clean_routine(question)

        # answers
        selector = "div.answerArea"
        tags = soup.select(selector)
        answers = [process_answer(tag) for tag in tags]

        document.question_badges = badges
        document.title = title
        document.question = question
        document.answers = answers

        return document
    except Exception as e:
        document.title = "ERROR"
        document.question = "ERROR"
        # print(e)
        # traceback.print_exc()
        return None

# -*- coding: utf-8 -*-

import flask
import mwapi  # type: ignore
import mwoauth  # type: ignore
import os
import random
import requests_oauthlib  # type: ignore
import string
import toolforge
from typing import Optional
import werkzeug
import yaml
from SPARQLWrapper import SPARQLWrapper, JSON

QUERIES = "queries"

sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

app = flask.Flask(__name__)

user_agent = toolforge.set_user_agent(
    'hauki',
    email='alicia@fagerving.se')

__dir__ = os.path.dirname(__file__)
try:
    with open(os.path.join(__dir__, 'config.yaml')) as config_file:
        app.config.update(yaml.safe_load(config_file))
except FileNotFoundError:
    print('config.yaml file not found, assuming local development setup')
    characters = string.ascii_letters + string.digits
    random_string = ''.join(random.choice(characters) for _ in range(64))
    app.secret_key = random_string

if 'oauth' in app.config:
    oauth_config = app.config['oauth']
    consumer_token = mwoauth.ConsumerToken(oauth_config['consumer_key'],
                                           oauth_config['consumer_secret'])
    index_php = 'https://www.wikidata.org/w/index.php'


@app.template_global()
def csrf_token() -> str:
    if 'csrf_token' not in flask.session:
        characters = string.ascii_letters + string.digits
        random_string = ''.join(random.choice(characters) for _ in range(64))
        flask.session['csrf_token'] = random_string
    return flask.session['csrf_token']


@app.template_global()
def form_value(name: str) -> flask.Markup:
    if 'repeat_form' in flask.g and name in flask.request.form:
        return (flask.Markup(r' value="') +
                flask.Markup.escape(flask.request.form[name]) +
                flask.Markup(r'" '))
    else:
        return flask.Markup()


@app.template_global()
def form_attributes(name: str) -> flask.Markup:
    return (flask.Markup(r' id="') +
            flask.Markup.escape(name) +
            flask.Markup(r'" name="') +
            flask.Markup.escape(name) +
            flask.Markup(r'" ') +
            form_value(name))


@app.template_filter()
def user_link(user_name: str) -> flask.Markup:
    user_href = 'https://www.wikidata.org/wiki/User:'
    return (flask.Markup(r'<a href="' + user_href) +
            flask.Markup.escape(user_name.replace(' ', '_')) +
            flask.Markup(r'">') +
            flask.Markup(r'<bdi>') +
            flask.Markup.escape(user_name) +
            flask.Markup(r'</bdi>') +
            flask.Markup(r'</a>'))


@app.template_global()
def authentication_area() -> flask.Markup:
    if 'oauth' not in app.config:
        return flask.Markup()

    if 'oauth_access_token' not in flask.session:
        return (flask.Markup(r'<a id="login" class="navbar-text" href="') +
                flask.Markup.escape(flask.url_for('login')) +
                flask.Markup(r'">Log in</a>'))

    access_token = mwoauth.AccessToken(**flask.session['oauth_access_token'])
    identity = mwoauth.identify(index_php,
                                consumer_token,
                                access_token)

    return (flask.Markup(r'<span class="navbar-text">Logged in as ') +
            user_link(identity['username']) +
            flask.Markup(r'</span>'))


def authenticated_session() -> Optional[mwapi.Session]:
    if 'oauth_access_token' not in flask.session:
        return None

    access_token = mwoauth.AccessToken(
        **flask.session['oauth_access_token'])
    auth = requests_oauthlib.OAuth1(client_key=consumer_token.key,
                                    client_secret=consumer_token.secret,
                                    resource_owner_key=access_token.key,
                                    resource_owner_secret=access_token.secret)
    return mwapi.Session(host='https://www.wikidata.org',
                         auth=auth,
                         user_agent=user_agent)


def run_sparql(query):
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    results = sparql.query().convert()
    return results["results"]["bindings"]


def get_query(query_name):
    with open(os.path.join(QUERIES, '{}.rq'.format(query_name))) as query_file:
        return query_file.read()


@app.route('/')
def index() -> str:
    languages = run_sparql(get_query("get_all_languages"))
    return flask.render_template('index.html', languages=languages)


def get_words_in_language(lang, offset=0, limit=100):
    query = get_query("get_words_in_language") % (lang, offset, limit)
    results = run_sparql(query)
    return [x["lemma"]["value"] for x in results]


def get_word(lexeme_id):
    query = get_query("lexeme_data") % (lexeme_id, lexeme_id, lexeme_id)
    return run_sparql(query)


def show_word_page(words, lang, languages):
    return flask.render_template('word.html',
                                 words=words, lang=lang,
                                 languages=languages)


def construct_glosses(lang, raw_word):
    glosses = []
    raw_glosses = [x
                   for x in raw_word
                   if x["description"]["value"] == "Gloss" and
                   x["value_"]["xml:lang"] == lang]
    raw_examples = [x
                    for x in raw_word
                    if x["description"]["value"] == "Usage example"]

    for raw_gloss in raw_glosses:
        gloss = {"id": "", "gloss": "", "examples": []}
        gloss["id"] = raw_gloss["value_Url"]["value"]
        gloss["gloss"] = raw_gloss["value_"]["value"]
        if raw_gloss.get("note"):
            gloss["notes"] = raw_gloss["note"]["value"]
        examples = [x for x in raw_examples if
                    x.get("demonstratesSense") and
                    x["demonstratesSense"]["value"] == gloss["id"]]
        for ex in examples:
            example = construct_example(ex)
            gloss["examples"].append(example)
        gloss["examples"] = sorted(gloss["examples"], key=lambda k: k['year'])
        glosses.append(gloss)
    return glosses


def construct_example(raw_example):
    example = {"year": "", "value": "", "title": "", "source_id": ""}
    if raw_example.get("note"):
        example["year"] = raw_example["note"]["value"]
    if raw_example.get("sourceLabel"):
        example["title"] = raw_example["sourceLabel"]["value"]
    if raw_example.get("source"):
        example["source_id"] = raw_example["source"]["value"]
    if raw_example.get("sourceLabel"):
        example["title"] = raw_example["sourceLabel"]["value"]
    example["value"] = raw_example["value_"]["value"]
    return example


def construct_examples(raw_word):
    examples = []
    raw_examples = [x for x in raw_word if x["description"]
                    ["value"] == "Usage example"]
    for raw_example in raw_examples:
        if not raw_example.get("demonstratesSense"):
            example = construct_example(raw_example)
            examples.append(example)
    return examples


def construct_forms(raw_forms):
    forms = []
    for raw_form in raw_forms:
        form = {"id": "", "value": "", "features": []}
        form["id"] = raw_form["form"]["value"].split("/")[-1]
        form["value"] = raw_form["formLabel"]["value"]
        form["features"] = sorted([
            x for x in raw_form["features"]["value"].split("|") if x != ""])
        forms.append(form)
    return forms


def construct_word(lang, raw_word, word_forms, l_id):
    word = {"lemma": "", "pos": "", "gender": "",
            "glosses": [], "examples": [], "id": ""}
    word["lemma"] = [x["value_"]["value"]
                     for x in raw_word
                     if x["description"]["value"] == "Lemma"][0]
    word["examples"] = construct_examples(raw_word)
    word["glosses"] = construct_glosses(lang, raw_word)
    word["id"] = l_id
    word["pos"] = [x["value_"]["value"]
                   for x in raw_word
                   if x["description"]["value"] == "Lexical category"][0]
    word["forms"] = construct_forms(word_forms)
    word["combines"] = [
        x for x in raw_word
        if x["description"]["value"] == "Combines" and
        x.get("value_")]
    word["compounds"] = [
        x["value_"]["value"] for x in raw_word
        if x["description"]["value"] == "In compound"
    ]
    word["derived_from"] = [x["value_"]["value"]
                            for x in raw_word if
                            x["description"]["value"] == "Derived from" and
                            x.get("value_")]
    word["derivations"] = [x["value_"]["value"]
                           for x in raw_word if
                           x["description"]["value"] == "Derivations" and
                           x.get("value_")]
    word["gender"] = [x["value_"]["value"]
                      for x in raw_word if
                      x["description"]["value"] == "Grammatical gender" and
                      x.get("value_")]
    word["forms_template"] = "forms_{}_{}".format(lang, word["pos"])
    return word


def get_lexeme_id(lang, word):
    query = get_query("get_lexeme_id_from_lemma") % (lang, word)
    results = run_sparql(query)
    return [x["l"]["value"].split("/")[-1] for x in results]


def get_word_forms(lexid):
    query = get_query("get_lexeme_forms") % lexid
    return run_sparql(query)


@app.errorhandler(404)
def page_not_found(e):
    return flask.redirect(flask.url_for('index'))


@app.route('/lex/<lang>/<word>')
def display(lang, word):
    lexeme_ids = get_lexeme_id(lang, word)
    if not lexeme_ids:
        flask.abort(404)
    to_display = []
    for lexid in lexeme_ids:
        word = get_word(lexid)
        word_forms = get_word_forms(lexid)
        word = construct_word(lang, word, word_forms, lexid)
        to_display.append(word)
    languages = run_sparql(get_query("get_all_languages"))
    return show_word_page(to_display, lang, languages)


@app.route('/browse', defaults={'lang': None})
@app.route('/browse/<lang>')
def language_browser(lang):
    languages = run_sparql(get_query("get_all_languages"))
    if not lang:
        return flask.render_template('language_browser_entry.html',
                                     languages=languages)
    offset = flask.request.args.get('from', default=0, type=int)
    limit = 100
    words = get_words_in_language(lang, offset, limit)
    navigation = {}
    if offset > limit:
        navigation["previous"] = offset - limit
    elif offset == 0:
        navigation["previous"] = None
    else:
        navigation["previous"] = "0"
    navigation["next"] = offset + limit
    return flask.render_template('language_browser.html',
                                 words=words, navigation=navigation,
                                 lang=lang, languages=languages)


@app.route('/autocomplete')
def autocomplete():
    searchfor = flask.request.args.get('query', default="", type=str)
    language = flask.request.args.get('lang', default="en", type=str)
    options = run_sparql(get_query("get_lemmas_starting_with") %
                         (language, searchfor))
    return flask.jsonify([x["label"]["value"] for x in options])


@app.route('/login')
def login() -> werkzeug.Response:
    redirect, request_token = mwoauth.initiate(index_php,
                                               consumer_token,
                                               user_agent=user_agent)
    flask.session['oauth_request_token'] = dict(zip(request_token._fields,
                                                    request_token))
    return flask.redirect(redirect)


@app.route('/oauth/callback')
def oauth_callback() -> werkzeug.Response:
    request_token = mwoauth.RequestToken(
        **flask.session.pop('oauth_request_token'))
    access_token = mwoauth.complete(index_php,
                                    consumer_token,
                                    request_token,
                                    flask.request.query_string,
                                    user_agent=user_agent)
    flask.session['oauth_access_token'] = dict(zip(access_token._fields,
                                                   access_token))
    return flask.redirect(flask.url_for('index'))


def full_url(endpoint: str, **kwargs) -> str:
    scheme = flask.request.headers.get('X-Forwarded-Proto', 'http')
    return flask.url_for(endpoint, _external=True, _scheme=scheme, **kwargs)


def submitted_request_valid() -> bool:
    """Check whether a submitted POST request is valid.

    If this method returns False, the request might have been issued
    by an attacker as part of a Cross-Site Request Forgery attack;
    callers MUST NOT process the request in that case.
    """
    real_token = flask.session.pop('csrf_token', None)
    submitted_token = flask.request.form.get('csrf_token', None)
    if not real_token:
        # we never expected a POST
        return False
    if not submitted_token:
        # token got lost or attacker did not supply it
        return False
    if submitted_token != real_token:
        # incorrect token (could be outdated or incorrectly forged)
        return False
    if not (flask.request.referrer or '').startswith(full_url('index')):
        # correct token but not coming from the correct page; for
        # example, JS running on https://tools.wmflabs.org/tool-a is
        # allowed to access https://tools.wmflabs.org/tool-b and
        # extract CSRF tokens from it (since both of these pages are
        # hosted on the https://tools.wmflabs.org domain), so checking
        # the Referer header is our only protection against attackers
        # from other Toolforge tools
        return False
    return True


@app.after_request
def deny_frame(response: flask.Response) -> flask.Response:
    """Disallow embedding the tool’s pages in other websites.

    If other websites can embed this tool’s pages, e. g. in <iframe>s,
    other tools hosted on tools.wmflabs.org can send arbitrary web
    requests from this tool’s context, bypassing the referrer-based
    CSRF protection.
    """
    response.headers['X-Frame-Options'] = 'deny'
    return response

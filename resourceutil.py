import re, string, time, traceback, requests
import nltk
from alchemyapi import AlchemyAPI

MULTIPLE_SPACES_REGEX = re.compile('\s\s+')
OTHER_THAN_SPACE_REGEX = re.compile('(\n|\t|\r)')
HASHTAG_REGEX = re.compile(ur'#|\uff03')
USERNAME_REGEX = re.compile(ur'\B[@\uff20][a-z0-9_]{1,20}')
EMAIL_REGEX = re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b')

# urls matching.
# Adapted from https://github.com/ianozsvald/twitter-text-python/blob/master/ttp/ttp.py
UTF_CHARS = ur'a-z0-9_\u00c0-\u00d6\u00d8-\u00f6\u00f8-\u00ff'
PRE_CHARS = ur'(?:[^/"\':!=]|^|\:)'
DOMAIN_CHARS = ur'([\.-]|[^\s_\!\.\/])+\.[a-z]{2,}(?::[0-9]+)?'
PATH_CHARS = ur'(?:[\.,]?[%s!\*\'\(\);:=\+\$/%s#\[\]\-_,~@])' % (UTF_CHARS, '%')
QUERY_CHARS = ur'[a-z0-9!\*\'\(\);:&=\+\$/%#\[\]\-_\.,~]'
PATH_ENDING_CHARS = r'[%s\)=#/]' % UTF_CHARS
QUERY_ENDING_CHARS = '[a-z0-9_&=#]'
URL_REGEX = re.compile('((%s)((https?://|www\\.)(%s)(\/(%s*%s)?)?(\?%s*%s)?))'
                       % (PRE_CHARS, DOMAIN_CHARS, PATH_CHARS,
                          PATH_ENDING_CHARS, QUERY_CHARS, QUERY_ENDING_CHARS),
                       re.IGNORECASE)

# stopwords
ENGLISH_STOPWORDS = set(nltk.corpus.stopwords.words('english'))
NON_ENGLISH_STOPWORDS = set(nltk.corpus.stopwords.words()) - ENGLISH_STOPWORDS

# stemmer
stemmer = nltk.stem.porter.PorterStemmer()

try:
    # emoji regex (UCS-4 format)
    EMOJI_REGEX = re.compile(u'[\U00010000-\U0010ffff]')
except re.error:
    # emoji regex (UCS-2 format)
    EMOJI_REGEX = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
# miscellaneous symbols regex
MISC_SYMBOLS_REGEX = re.compile(u'[\u20A0-\u27BF]')

# Alchemy API
alchemyapi = AlchemyAPI()

def sanitize_content(content):
    '''Sanitize content: remove hashtag character, remove usernames,
       remove email addresses, remove emoji characters, lowercase.'''
    sane_content = content
    # remove hashtag characters
    sane_content = HASHTAG_REGEX.sub(' ', sane_content)
    # remove usernames
    sane_content = USERNAME_REGEX.sub('', sane_content)
    # remove email addresses
    sane_content = EMAIL_REGEX.sub('', sane_content)
    # remove emoji characters and various similar symbols
    sane_content = EMOJI_REGEX.sub(' ', sane_content)
    sane_content = MISC_SYMBOLS_REGEX.sub(' ', sane_content)
    # trim spaces and remove multiple spaces
    sane_content = sane_content.strip()
    sane_content = OTHER_THAN_SPACE_REGEX.sub(' ', sane_content)
    sane_content = MULTIPLE_SPACES_REGEX.sub(' ', sane_content)
    # lowercase
    sane_content = sane_content.lower()
    return sane_content

def extract_content_from_url(content):
    '''Look for http(s) link inside content and extract the relevant information
       from these links using AlchemyAPI. This method extracts the content from 
       the first url found, even if there is multiple urls.'''
    url_matcher = URL_REGEX.search(content)
    if url_matcher is not None:
        url = format_url(url_matcher.group(0))
        response = alchemyapi.text('url', url)
        if response['status'] == 'OK':
            new_content = URL_REGEX.sub('', content + ' ' + response['text'])
            return new_content
        else:
            return content
    else:
        return content

def format_url(url):
    # Check for urls without http(s)
    pos = url.find('http')
    if pos != -1:
        full_url = url[pos:]

    # Find the www and force http://
    else:
        pos = url.lower().find('www')
        full_url = 'http://' + url[pos:]

    return full_url

def extract_stems(content):
    '''Sanitize, remove stopwords, tokenize and stem the content.
       Returns a list of stems'''
    # sanitize
    sane_content = sanitize_content(content)
    # tokenize
    tokens = nltk.wordpunct_tokenize(sane_content)
    # remove stopwords
    tokens = [word for word in tokens if word not in ENGLISH_STOPWORDS]
    # remove special characters
    tokens = [token for token in tokens if token.isalnum()]
    # stemming
    stems = [stemmer.stem(token) for token in tokens]
    return stems

def extract_entities(content):
    '''Sanitize content and use TAGME API to extract entities.
       Returns a list of entities and their relevance score rho: [{'entity':entity, 'rho'=rho}, ...]'''
    entities = []
    # sanitize
    sane_content = sanitize_content(content)
    parameters = {
        'key':'rslondon2014',
        'text':sane_content,
        'lang':'en'
    }
    url = 'http://tagme.di.unipi.it/tag'

    retry = True
    retry_count = 0
    while retry:
        try:
            time.sleep(0.5)
            response = requests.get(url, params=parameters)
            response = response.json()
            retry = False
        except requests.Timeout:
            if retry_count < 9:
                retry = True
                retry_count = retry_count + 1
            else: 
                return []
        except:
            return []

    for annotation in response['annotations']:
        try:
            entities.append({'entity': annotation['title'], 'rho': annotation['rho']})
        except:
            print '>>> traceback <<<'
            traceback.print_exc()
            print '>>> end of traceback <<<\n' 
    return entities 
 
def is_english(text):
    '''Language detection using nltk.
       Adapted from http://www.algorithm.co.il/blogs/programming/python/cheap-language-detection-nltk/'''
    text = sanitize_content(text)
    words = set(nltk.wordpunct_tokenize(text))
    return len(words & ENGLISH_STOPWORDS) > len(words & NON_ENGLISH_STOPWORDS)

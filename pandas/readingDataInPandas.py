import json
import logging
import os
import traceback
import threading
import sqlite3

try:
    # py3 imports
    from urllib.parse import urljoin, unquote
except ImportError:
    # py2 import
    from urlparse import urljoin
    from urllib import unquote


from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render_to_response, render
from django.views.decorators.csrf import csrf_exempt
from celery.task.control import revoke

from sd.wp_celery import app as celery_app

from django_apps.link.models import Link
from django_apps.registration.models import UserProfile
from django_apps.recipient.models import SocialAccount
from django_apps.recipient.search_url import search_post_api_method
from django_apps.recipient.tasks import _save_job_results_to_link
from django_apps.recipient.twitterFetchData import (create_collection, create_collection_with_sleep, home_timeline,
                                                    TW_HAS_MEDIA_FIELD, wiki_permutations, USE_CSV_FOR_VALIDRECIPIENTS,
                                                    lookup_for_valid_recipient_by_tw_account, TWITTER_CATEGORIES_MAP,
                                                    additional_categorization_map)
from django_apps.recipient.videoResults import fetch_youtube_videos
from django_apps.recipient.util import (get_cropped_image_view, get_link_details_from_cache, save_link_info_to_cache,
                                        get_tw_details_from_cache, get_multiple_tweets_details_from_cache, CSV_SECTIONS,
                                        get_csv_rows_by_wiki_ids_and_twitter_id, redis_cache as csv_cache, get_domain_from_url)
from django_apps.recipient.demo_api2 import update_reading_list_metadata
from django_apps.recipient.editorData import dynamic_categorization_conditional_wordslist

tracing_logger = logging.getLogger('recipient-demo-api-tracing')


#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def recipient_debug(request, query):
#     matches = [x for x in get_results_for_query(query) if isinstance(x, dict)]
#     format_dict = lambda d: "\n\n".join(["%s: %s" % (k, d[k]) for k in d.keys()])
#     text = "\n\n--------------------\n--------------------\n\n".join([format_dict(e) for e in matches])
#     return HttpResponse(text, mimetype="text/plain")
#
#
# # End conveniences
#
# """ ADD A RECIPIENT DIALOG """
# # This is the wizard used to add recipients to the site by looking them up on wikipedia
# # getting the metadata from that source, and dynamically adding them to the database.
# # You can find the launch point for this wizard at /townhall and search results page.
# # More info is available on dialogs here
# # https://github.com/wpdevs/wp/wiki/Modal-Dialog-Documentation
# # https://github.com/wpdevs/wp/wiki/Javascript-Dialogs-Overview
#
# # The wizard gets metadata from wikipedia from here: https://github.com/wpdevs/wp/tree/master/tp-apps/wp_scraper
#===============================================================================

# """ ADD A RECIPIENT: Check for URL conflict """
class UrlException(Exception):
    """
    An exception that provides a url parameter; a url
    may be an absolute url or a url like /georgeclooney.
    """

    def __init__(self, url):
        self.url = url


class SourceUrlConflict(UrlException):
    pass


class RecipientUrlConflict(UrlException):
    pass


class NoImageException(UrlException):
    pass


class ImageCropException(Exception):
    pass


class CrawlFailException(Exception):
    pass

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# class MailbagConflictException(Exception):
#     """
#     An exception thrown when a user tries to create a
#     mailbag for which the same slug/recipient pair
#     already exists.
#     """
#
#     def __init__(self, mailbag_id):
#         self.mailbag_id = mailbag_id
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: Check if entity is a brand of a larger brand """
# def is_child_brand(child_name, parent_name):
#     """
#     Checks for relationships like Nike -> Nike Vision.
#     The rule is: if the first word of the parent name
#     is contained anywhere in the child name, return True.
#     """
#     # For instance, we would want Coca-Cola Zero to be a mailbag because it's
#     # a child of Coca-Cola Company, but KFC should not have a brand choice
#     # screen because KFC is not contained
#
#     # Strip out commas for Nike, Inc. et al.
#     parent_words = parent_name.replace(",", "").lower().split()
#     filtered_words = [e for e in parent_words if e != "the"]
#     if filtered_words:
#         return filtered_words[0] in child_name.lower()
#     else:
#         return False
#===============================================================================
#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: Truncate Bio """
# def truncate_description(s):
#     """
#     Break the string at the end of the first sentence after 165 characters have
#     been seen.
#     Used for shortening mailbag descriptions.
#     """
#     # First period followed by any number of spaces and a capital letter at 165 characters or less.
#     # Unless the character before the period is also preceded by a period.
#
#     r = "[^A-Z]\.\s+[A-Z]" # A non-capital, followed by a period, followed by whitespace, followed by a capital.
#     OFFSET = 2 # OFFSET for the non-capital letter and the period.
#     result = re.search(r, s)
#     if result:
#         sentence_end = result.start() + OFFSET
#         return s[:sentence_end]
#     else:
#         return s
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: Create a Maibag from a wikipedia result """
# # This is done when we know the result has a parent and that it doesn't deserve to have its own recipient object
# def mailbag_from_query(query, user):
#     """Given a query, scrape a recipient from wikipedia and create it."""
#     matches = [e for e in get_results_for_query(query) if isinstance(e, dict)]
#
#     if matches:
#         crawl_result = matches[0]['scraper_result']
#         return wikipedia_create_mailbag(
#             crawl_result,
#             user,
#             False)
#     else:
#         raise CrawlFailException()
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def wikipedia_create_mailbag(crawl_result, user, GET=None):
#     """
#     Create a mailbag scraped from wikipedia. This is used when the user tries to
#     add a recipient, but the recipient is more appropriately a mailbag. E.g.,
#     if a user creates the recipient Air Jordans, they would be given the option
#     to make Air Jordans a mailbag whose recipient is Nike.
#     """
#     # IMPORTANT
#     # Don't use this function unless the mailbag will automatically
#     # a parent!
#
#     from mailbag.models import Mailbag
#
#     if GET is None:
#         GET = {}
#
#     source_url = u'http://en.wikipedia.org/wiki/%s' % crawl_result['id'][0]
#
#     photo_filename = GET.get('orig_fname')
#
#     name = crawl_result['name'][0]
#     desc = truncate_description(clean_wikimarkup(crawl_result['article_text']).split('==', 1)[0])
#
#     parent_id = crawl_result['parent_ids'][0]
#
#     user_profile = user.get_profile()
#
#     # In this case, the parent is actually the recipient of the mailbag,
#     # not really a parent at all.
#     try:
#         recipient = Recipient.objects.get(name=parent_id)
#     except Recipient.DoesNotExist:
#         recipient = recipient_from_query(parent_id, user)
#
#     slug = slugify(name)
#
#     # Make sure that this mailbag doesn't already exist.
#     # If it does raise an exception.
#     try:
#         mailbag = Mailbag.objects.get(slug=slug, recipient=recipient)
#         raise MailbagConflictException(mailbag.id)
#     except Mailbag.DoesNotExist:
#         pass
#
#     skip_image = GET.get('skipImage', False)
#     if skip_image == 'false':
#         skip_image = False
#
#     if not skip_image and not photo_filename:
#         raise NoImageException('')
#
#
#     kwargs = {
#         'name': name,
#         'slug': slug,
#         'creator': user_profile,
#         'recipient': recipient,
#         'desc': desc,
#         'mtype': 'product-work',
#         }
#
#     if photo_filename:
#         photo = photo_crop_success(Recipient,
#                                    'photo',
#                                    photo_filename,
#                                    (250, 210),
#                                    (250, 250),
#                                    GET)
#         photo_credit = RecipientPhotoCredit.objects.create(image_credit="See Wikipedia",
#                                                            source_explaination="fair use",
#                                                            website_source=crawl_result.get('image', [''])[0])
#
#         kwargs.update({
#                 'photo_orig': photo_filename,
#                 'photo': photo,
#                 'photo_credit': photo_credit,
#                 })
#         # These weren't working because the photo is just a SimpleUploadedFile object.
#         #d = {'photo_w': photo.width,
#         #     'photo_h': photo.height,
#         #     }
#
#     return Mailbag.objects.create(**kwargs)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: Add parent entity in the background if its not already on the site """
# def recipient_from_query(query, user):
#     """Given a query, scrape a recipient from wikipedia and create it."""
#     # This is currently just used to create parents in the background,
#     # which is why auto_resize is set to True.
#     recipient_url = query.lower()
#     matches = [e for e in get_results_for_query(query) if isinstance(e, dict)]
#
#     if matches:
#         crawl_result = matches[0]['scraper_result']
#         return wikipedia_create_recipient(
#             crawl_result,
#             user,
#             recipient_url,
#             True)
#     else:
#         raise CrawlFailException()
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: Create Recipient from data of a user query """
# def wikipedia_create_recipient(crawl_result, user, recipient_url, auto_resize=False, GET=None):
#     """Create a recipient using data from wikipedia."""
#
#     if GET is None:
#         GET = {}
#
#     # Create source and recipient urls
#     source_url = u'http://en.wikipedia.org/wiki/%s' % crawl_result['id'][0]
#     if recipient_url:
#         recipient_url = _space_re.sub('', recipient_url)
#     else:
#         recipient_url = match_to_url(crawl_result)
#
#     # Manage this better
#     skip_image = GET.get('skipImage', False)
#     if skip_image == 'false':
#         skip_image = False
#
#     photo_filename = GET.get('orig_fname')
#     # If we are automatically resizing it, try to pull from the crawl result.
#     if photo_filename is None and auto_resize:
#         photo_filename = crawl_result.get('image', [''])[0]
#
#     rcpt_type = (crawl_result.get('type') or [''])[0].lower()
#
#     # Checks for various errors.
#     # Recipient has not been created before, does not conflict with
#     # another recipient, and does not claim to have a photo
#     # but is lacking it.
#     if Recipient.objects.source_url_conflict(source_url):
#         raise SourceUrlConflict(source_url)
#
#     if Recipient.objects.url_conflict(recipient_url):
#         raise RecipientUrlConflict(recipient_url)
#
#     if not photo_filename and not skip_image and not auto_resize:
#         raise NoImageException(recipient_url)
#
#
#     rkwargs = {
#         'name': crawl_result['name'][0],
#         'bio':  clean_wikimarkup(crawl_result['article_text']).split('==', 1)[0],
#         'aliases': json.dumps(get_aliases(crawl_result)),
#         'rcpt_type': rcpt_type,
#         'source_url': source_url,
#         'source_id': u'wikipedia:%s' % crawl_result['id'][0],
#         'url': recipient_url,
#         'name_needs_article': bool(_article_re.search(crawl_result['article_text'].splitlines()[0]),),
#         'related_companies': json.dumps(crawl_result.get("related_companies", [])),
#         'related_people': json.dumps(crawl_result.get("related_people", [])),
#         'created_by': user,
#         }
#
#     if photo_filename:
#         if auto_resize:
#             try:
#                 resize_result = auto_resize_from_url(photo_filename, (250, 210))
#                 resize_result.save()
#                 photo = photo_save(Recipient, 'photo', resize_result.imagename, resize_result.image)
#             except BadImageException:
#                 photo = None
#
#         else:
#             photo = photo_crop_success(Recipient,
#                                               'photo',
#                                               photo_filename,
#                                               (250, 210),
#                                               (250, 250),
#                                               GET)
#
#         rkwargs['photo'] = photo
#         if photo:
#             rkwargs['photo_credit'] = RecipientPhotoCredit.objects.create(image_credit="See Wikipedia",
#                                                                           source_explaination="fair use",
#                                                                           website_source=crawl_result.get('image', [''])[0])
#         else:
#             rkwargs['photo_credit'] = None
#
#     if crawl_result.get('date_of_birth'):
#         rkwargs["birth_date"] = crawl_result['date_of_birth'][0]
#     if crawl_result.get('date_of_death'):
#         rkwargs["death_date"] = crawl_result['date_of_death'][0]
#
#     recipient = Recipient.objects.create(**rkwargs)
#
#     tags = RecipientLabel.objects.filter_by_typeslug(*crawl_result.get('tags', []))
#     for tag in tags:
#         RecipientEditorLabel.objects.create(recipient=recipient,
#                                             label=tag,
#                                             name=tag.name,
#                                             slug=tag.slug)
#
#
#     # Handle the creation of parents
#     # Parent_id is actually a name, like 'Starbucks', or
#     # maybe Starbucks_(brand)
#
#     # These are not legitimate parents but they're fooling the scraper.
#     excluded_parents = set(['brand',])
#
#     if 'parent_ids' in crawl_result:
#         parent_ids = [e for e in crawl_result['parent_ids'] if e not in excluded_parents]
#
#         for parent_id in parent_ids:
#             source_id = "wikipedia:%s" % parent_id
#             if recipient.rcpt_type in ("organization", "company", "brand"):
#                 parents = Recipient.objects.filter(source_id=source_id) # Should never be more than one.
#                 if parents:
#                     parent = parents[0]
#                 else:
#                     try:
#                         parent = recipient_from_query(parent_id, user)
#                     except CrawlFailException:
#                         parent = None
#                     # Not sure why this is getting thrown, but it is.
#                     except SourceUrlConflict as e:
#                         parent = Recipient.objects.get(source_url=e.url)
#
#                 if parent:
#                     recipient.parents.add(parent)
#
#     return recipient
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: User Adds Custom Recipient (One not in wikipedia) """
# def user_create_recipient(req_data, user):
#     """Create a recipient using user-supplied data."""
#
#     # Attrs off of req_data
#     # Definite: name, bio, type,
#     # Possible: orig_fname, photo_explanation, fairuse_webpage, fairuse_reason, altnames
#
#     rkwargs = {
#         'name': req_data['name'],
#         'bio':  req_data['bio'],
#         'rcpt_type': req_data['type'].lower(),
#         'source_id': u"usergen_%s:%s" % (user, req_data['name']),
#         'url':  remove_symbols(req_data['name']),
#         'aliases': '[]',
#         'created_by': user,
#         }
#
#     # Manage photo information
#     if req_data.get('orig_fname'):
#         credit_kwargs = {
#             "source_explaination": req_data.get("photo_explanation")
#             }
#         credit = req_data.get("photo_credit")
#         if credit and credit.lower() != "optional":
#             credit_kwargs["image_credit"] = credit
#         if req_data.get("photo_explanation") == "fair use":
#             credit_kwargs["website_source"] = req_data.get('fairuse_webpage')
#             credit_kwargs["fairuse_reason"] = req_data.get('fairuse_reason')
#         rkwargs["photo"] = photo_crop_success(Recipient,
#                                               'photo',
#                                               req_data['orig_fname'],
#                                               (250, 210),
#                                               (250, 250),
#                                               req_data)
#         rkwargs["photo_credit"] = RecipientPhotoCredit.objects.create(**credit_kwargs)
#
#     # Manage recipient aliases
#     if req_data['altnames'] != 'Separate each name by commas':
#         rkwargs['aliases'] = json.dumps([e.strip() for e in req_data['altnames'].split(',') if e.strip()])
#
#     return Recipient.objects.create(**rkwargs)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: YAHOO BOSS RESULTS """
# # We use this if we get 0 results from our initial query to wikipedia and want to see if the user
# # misspelled the name by supplying the yahoo results to wikipedia pages and letting them pick
# def yahoo_boss_search(query, sites='en.wikipedia.org/wiki/'):
#     """
#     Use yahoo search api for a query, return a boolean
#     representing the success of the search and a list of id's.
#     """
#
#     url =  "http://yboss.yahooapis.com/ysearch/web"
#     params = {
#         'oauth_version': "1.0",
#         'oauth_nonce': oauth2.generate_nonce(),
#         'oauth_timestamp': int(time.time()),
#         'q': quote(query),
#         'sites': quote(sites),
#         'format': 'json',
#     }
#
#     consumer = oauth2.Consumer(key=settings.YAHOO_CONSUMER_KEY, secret=settings.YAHOO_CONSUMER_SECRET)
#     req = oauth2.Request(method="GET", url=url, parameters=params)
#     signature_method = oauth2.SignatureMethod_HMAC_SHA1()
#     req.sign_request(signature_method, consumer, None)
#
#     try:
#         response = urllib2.urlopen(req.to_url())
#         if response.getcode() == 200:
#             wikipedia_ids = []
#             boss_response = json.loads(response.read())['bossresponse']
#             results = boss_response.get('web', {}).get('results', [])
#             for result in results:
#                 split_result = result['clickurl'].split('/')
#                 wikipedia_ids.append(split_result[len(split_result) - 1])
#
#             return True, wikipedia_ids
#         else:
#             return False, None
#     except urllib2.URLError as err:
#         return False, None
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def yahoo_boss_filter(results, q, d):
#     # now that we have some results, we need to put them back into the crawler
#     # we only take the first YAHOO_SEARCH_RESULTS_LIMIT number of results to do the matches on
#     matches = []
#     counter = 1
#     for result in results:
#         # check first criteria
#         # First letter of the first word of query start either the Article title first word or second word.
#         #Bradfirst_letter_query = q[0]
#         #Bradsplit_result = result.split('_')
#         #Bradsplit_1 = split_result[0]
#         #Bradif len(split_result) > 1:
#         #Brad    split_2 = split_result[1]
#         #Brad    if first_letter_query != split_1[0] and first_letter_query != split_2[0]:
#         #Brad        continue
#         #Bradelse:
#         #Brad    if first_letter_query != split_1[0]:
#         #Brad        continue
#
#         # second criteria
#         # One of the words they've typed in the query is in the Article title.   (assuming this is at least two words)
#         #Bradq_words = q.split(' ')
#         # split up the words and only do this test if we have at least two words
#         #Bradif len(q_words) > 1:
#         #Brad    word_found = False
#         #Brad    # loop through all the query words
#         #Brad    for q_word in q_words:
#         #Brad        # if we find the word in the search results, we're good
#         #Brad        if q_word in result:
#         #Brad            word_found = True
#         #Brad            break
#
#         #Brad    # if we don't find the word, this search result is no good, we skip it
#         #Brad    if not word_found:
#         #Brad        continue
#
#         # third criteria
#         # No pages where the Article starts "Category:" or "List of".  Please note there is no space between Category:Categoryname.
#         if result.startswith('Category:'):
#             continue
#         if result.startswith('List_of'):
#             continue
#
#         result_matches = [x for x in get_results_for_query(result) if isinstance(x, dict)]
#         matches.extend(result_matches)
#
#         # FIXME: looks like this is undercounting by one.
#         # Better to use enumerate on results.
#         counter += 1
#         if counter > settings.YAHOO_SEARCH_RESULTS_LIMIT:
#             break
#
#     return matches
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A RECIPIENT: DIALOG VIEWS """
# # Views start here.
#
# def add_test(request, template="recipient/add_dialog_test.html"):
#     return render(request, template, {})
#
# def add(request, template="recipient/add_dialog.html"):
#     """
#     Initial view for the add_recipient dialog. Stub view necessary to render the
#     appropriate dialog snippet.
#     """
#     return render(request, template, {})
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# @csrf_exempt
# def process_thumbnail(request):
#     """
#     Creates a thumbnail for a given id if it does not exist.
#     """
#     #FIXME: half of this code can be deleted since we're always returning a blank image.
#
#     id = request.GET['id']
#     wikiurl = request.GET['url']
#     url = wikiimages.get_thumbnail_or_none(id)
#     if not url:
#         try:
#             url = wikiimages.generate_thumbnail(wikiurl, id)
#         except IOError:
#             url = None
#     if not url:
#         img = ''
#     else:
#         name = id.replace('_', ' ')
#         img = u'<img class="match_thumb" src="%s" alt="%s" />' % (url, name)
#
#     # We will always just return no image and the next person viewing
#     # it will get the pleasant experience.
#     img = ''
#     return HttpResponse(json.dumps({"img": img}),
#                         mimetype="application/json")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# @csrf_exempt
# def dialog_check_id(request):
#     """
#     This view just checks to see if an id from wikipedia is already in the
#     database.
#     """
#     title = htmlid_to_id(request.GET["recipient_id"])
#
#     matches = [x for x in get_results_for_query(title)
#                if isinstance(x, dict)]
#
#     if len(matches) != 1:
#         return HttpResponse("")
#
#     crawl_result = matches[0]['scraper_result']
#
#     source_url = u'http://en.wikipedia.org/wiki/%s' % crawl_result['id'][0]
#
#     # Check to see if the recipient exists already.
#     # If not, create one (how is HttpResponse creating one?)
#     if Recipient.objects.source_url_conflict(source_url):
#         ctx = { 'recipient': Recipient.objects.get(source_url=source_url) }
#         return render(request, "recipient/add_dialog/recipient_exists.html", ctx)
#     else:
#         return HttpResponse("")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# _space_re = re.compile("\s+")
# @csrf_exempt
# def urltest(request):
#     """
#     This view just checks to see if a slug is free and valid.
#     This is necessary because topic detail, category detail, and recipient detail all share the root urlconf space.
#     """
#
#     if not request.is_ajax():
#         return HttpResponse("")
#     url = request.GET.get('url', '').strip().strip("/").lower()
#     url = _space_re.sub('', url)
#     if not url:
#         response = "empty"
#     elif Recipient.objects.filter(url__exact = url).exists():
#         response = "conflict"
#     else:
#         response = "good"
#     return HttpResponse(json.dumps({"url_status": response}),
#                         mimetype="application/json")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def get_user_or_anonymous(request):
#     if request.user.is_anonymous():
#         return User.objects.get(username='anonymous')
#     else:
#         return request.user
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def create_recipient(request, crawl_result, pretty_title, auto_resize=False):
#     """
#     A wrapper around wikipedia_create_recipient to do some error handling.
#     """
#
#     user = get_user_or_anonymous(request)
#
#     try:
#         recipient = wikipedia_create_recipient(crawl_result,
#                                                user,
#                                                request.GET.get('new_url'),
#                                                auto_resize,
#                                                request.GET.copy())
#
#         recipient.submit_to_townhall(user)
#         recipient_uri = request.build_absolute_uri(reverse("recipient_detail", args=[recipient.id]))
#
#         ctx = {
#             'title': pretty_title,
#             'recipient': recipient,
#             'recipient_uri': recipient_uri
#             }
#
#         return render(request, "recipient/add_dialog/success.html", ctx)
#
#     # A recipient already exists from the same url.
#     # (e.g. en.wikipedia.org/wiki/George_Clooney has already been scraped).
#     except SourceUrlConflict as e:
#         ctx = {
#             'title': pretty_title,
#             'recipient': Recipient.objects.get(source_url=e.url)
#             }
#         return render(request, "recipient/add_dialog/recipient_exists.html", ctx)
#
#     # The recipient url conflicts with an already existing url.
#     # e.g. try to add John Williams when we already have a John Williams
#     # at /johnwilliams
#     except RecipientUrlConflict as e:
#
#         ctx = {
#             'title': pretty_title,
#             'bad_url': e.url,
#             'aliases': get_aliases(crawl_result)
#             }
#         if request.GET.get('orig_fname'):
#             # This is where the recipient data is getting passed in.
#             ctx['json_data'] = json.dumps({'orig_fname': request.GET['orig_fname']})
#         return render(request, "recipient/add_dialog/urlconflict.html", ctx)
#
#     # There's an image, but it doesn't seem to have been cropped yet.
#     # Redirect to the crop page.
#     except NoImageException as e:
#         request.GET = request.GET.copy()
#         request.GET["img"] = crawl_result.get('image')[0]
#         try:
#             return dialog_photo_add(request, {'recipient_id': request.GET.get('recipient_id'), 'new_url': e.url})
#         except ImageCropException:
#             # If image creation fails (presumably because there's no image
#             # Just create it without the image.
#             request.GET = request.GET.copy()
#             request.GET['skipImage'] = True
#             request.GET['orig_fname'] = None
#             return create_recipient(request, crawl_result, pretty_title, auto_resize)
#===============================================================================


#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def create_mailbag(request, crawl_result, pretty_title):
#
#     try:
#         mailbag = wikipedia_create_mailbag(crawl_result,
#                                            get_user_or_anonymous(request),
#                                            request.GET.copy())
#     except MailbagConflictException as e:
#         from mailbag.models import Mailbag
#         mailbag = Mailbag.objects.get(id=e.mailbag_id)
#
#     # Placeholder for future No image logic.
#     except NoImageException as e:
#         request.GET = request.GET.copy()
#         request.GET["img"] = crawl_result.get('image')[0]
#         return dialog_photo_add(request, {'recipient_id': request.GET.get('recipient_id')})
#
#     mailbag_uri = request.build_absolute_uri(reverse("generic_second_level", args=[mailbag.recipient.url, mailbag.slug]))
#
#     ctx = {
#         'title': pretty_title,
#         'mailbag': mailbag,
#         'mailbag_uri': mailbag_uri,
#         }
#     return render(request, "recipient/add_dialog/mailbag_success.html", ctx)
#===============================================================================


#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def dialog_brand(request):
#     """Brand Dialog."""
#
#     type_decision = request.GET.get("type_decision")
#
#     title = htmlid_to_id(request.GET["recipient_id"])
#     pretty_title = title.replace('_', ' ')
#
#     matches = [e for e in get_results_for_query(title) if isinstance(e, dict)]
#     crawl_result = matches[0]['scraper_result']
#
#     # Seems like this page doesn't do much anymore.
#     # What it should do is probably just route to the appropriate image creation screen.
#
#     if type_decision == 'mailbag':
#         return create_mailbag(request, crawl_result, pretty_title)
#     else:
#         return create_recipient(request, crawl_result, pretty_title)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def dialog_direct(request, use_photo=True, extra_data=None):
#     """
#     View to determine the dialog screen after dialog_direct.
#     """
#
#     user = get_user_or_anonymous(request)
#
#     req_data = {}
#
#     if extra_data is not None:
#         req_data.update(extra_data)
#
#
#     for k,v in request.GET.iteritems():
#         req_data[k] = v
#
#     # Custom recipient is calling this view with a POST
#     # Presumably, any method that is creating a recipient
#     # should be using a POST.
#
#     for k,v in request.POST.iteritems():
#         req_data[k] = v
#
#     topic_id = req_data.get('topic_id')
#
#     # Let's use an explicit user_generated property.
#     if req_data.get('name') and req_data.get('bio'):
#         recipient = user_create_recipient(req_data, user)
#         pretty_title = req_data['name']
#
#         # Submit the recipient to townhall for approval and generate the recipient's new uri.
#         recipient.submit_to_townhall(user)
#         recipient_uri = request.build_absolute_uri(reverse("recipient_detail", args=[recipient.id]))
#
#         if topic_id:
#             from mailbag.models import TopicSeed # Avoid circular import
#             topic = TopicSeed.objects.get(id=topic_id)
#             mailbag = topic.create_topic_mailbag(recipient)
#             ctx = {
#                 'title': pretty_title,
#                 'recipient': recipient,
#                 'recipient_uri': recipient_uri,
#                 'topic': topic,
#                 'mailbag': mailbag,
#                 }
#             return render(request, "recipient/add_dialog/topic_success.html", ctx)
#
#
#         ctx = {
#             'title': pretty_title,
#             'recipient': recipient,
#             'recipient_uri': recipient_uri
#             }
#         return render(request, "recipient/add_dialog/success.html", ctx)
#
#     title = htmlid_to_id(req_data["recipient_id"])
#
#     # Pretty title for show.
#     pretty_title = title.replace('_', ' ')
#
#     matches = [e for e in get_results_for_query(title) if isinstance(e, dict)]
#     crawl_result = matches[0]['scraper_result']
#
#     child_name = crawl_result['name'][0]
#     parent_ids = crawl_result.get('parent_ids', [])
#     recipient_type = (crawl_result.get('type') or [''])[0]
#
#     # Automatically create a product mailbag.
#     if recipient_type == 'product':
#         return create_mailbag(request, crawl_result, pretty_title)
#
#     # Check that a recipient type has not been chosen.
#     # If not, route to a brand disambiguation page if necessary.
#     type_decision = request.GET.get("type_decision")
#     if not type_decision:
#         for parent_id in parent_ids:
#             if is_child_brand(child_name, parent_id):
#                 ctx = {
#                     'child_name': child_name,
#                     'parent_name': parent_id,
#                     }
#
#                 return render(request, "recipient/add_dialog/brand.html", ctx)
#
#     # Check to see if this is being loaded from a topic page.
#     if topic_id:
#         # If a topic_id has been supplied, create a mailbag
#         # for the new recipient in that topic, and redirect
#         # to the topic success dialog.
#         from mailbag.models import TopicSeed # Avoid circular import
#         topic = TopicSeed.objects.get(id=topic_id)
#         recipient = wikipedia_create_recipient(crawl_result, user, None, True)
#         recipient.submit_to_townhall(user)
#         mailbag = topic.create_topic_mailbag(recipient)
#         ctx = {
#             'title': recipient.name,
#             'recipient': recipient,
#             'recipient_uri': request.build_absolute_uri(reverse("recipient_detail", args=[recipient.id])),
#             'topic': topic,
#             'mailbag': mailbag,
#             }
#         return render(request, "recipient/add_dialog/topic_success.html", ctx)
#
#     if type_decision == 'mailbag':
#         return create_mailbag(request, crawl_result, pretty_title)
#     else:
#         return create_recipient(request, crawl_result, pretty_title)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def dialog_search(request):
#     """
#     Render a variety of templates, depending on the search results.
#     """
#
#     # It seems that these are the disambiguation rules.
#     # If disambiguation_level == 0: show the most likely result
#     # If disambiguation_level == 1: show the second most likely result
#     # If disambiguation_level >1: show a user-created recipient dialog.
#     # Presumably, this should work together with the multi-dialog
#     # response, which should show multiple recipient radio buttons
#     # if there are three or more candidates.
#
#
#     def render_results(snippet, context):
#         """
#         Helper function to render a given template.
#         """
#         template = "recipient/add_dialog/%s.html" % snippet
#         return render(request, template, context)
#
#
#     query = request.GET.get("q", '')
#     if query == query.lower():
#         query = query.title()
#
#
#     # This is the current disambiguation level.
#     # We return less likely responses based on how high the disambiguation level is.
#     # This should probably be passed in through the state variable.
#     disambiguation_level = int(request.GET.get("disambiguationLevel", 0))
#
#     # A topic id has been passed into the GET
#     topic = request.GET.get('topic')
#
#     # First, we make sure that we have a legitimate request.
#
#     # no parameters, render the search dialog.
#     if not query:
#         return render_results("search", {"topic": topic})
#
#     # User-created recipient page.
#     if disambiguation_level > 1:
#         return render_results("new", {"query": query})
#
#
#     # OK, now we know we have a parameter. Let's rsearch for it..
#     matches = get_results_for_query(query, disambiguation_level)
#
#     # here we have NO results, so we fall back to Yahoo Boss
#     # Seems like the success variable is not necessary, can just
#     # return an empty list if it fails.
#     if len(matches) == 0 and settings.YAHOO_SEARCH_ENABLED and disambiguation_level == 0:
#         matches = []
#         success, results = yahoo_boss_search(query)
#         if success:
#             matches = yahoo_boss_filter(results, query, disambiguation_level)
#
#     # Handle cases where a search does not successfully return a value.
#     if len(matches) == 0:
#         if disambiguation_level > 0:
#             return render_results("new", {"query": query})
#         else:
#             # Different no matches screens if you're coming from a multi-screen or not.
#             from_multi = request.GET.get("frommulti")
#             if from_multi and int(from_multi):
#                 # If the proposed recipient is not valid (not a person or company)
#                 # This screen will be rendered.
#                 return render_results("nomatches-multi", {})
#             else:
#                 # Return a plain no matches screen.
#                 # Very similar to nomatches-multi.
#                 return render_results("nomatches", {})
#
#     if len(matches) == 1:
#         # Hack
#         # Fix a bug that was making thumbnail not show up.
#         # Would be a good idea to track down where the colon was
#         # getting replaced in the first place.
#         match = matches[0]
#         if match['thumbnail']:
#             match['thumbnail'] = match['thumbnail'].replace("%3A", ":")
#
#         return render_results("direct", {"match": match })
#     else:
#         return render_results("multi", {"matches": matches})
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# @csrf_exempt
# def dialog_photo_add(request, extra_data=None):
#     """Dialog for adding or cropping photo."""
#
#     if extra_data is None:
#         extra_data = {}
#
#     some_image = request.GET.get('img') or request.FILES.get('img')
#     if not some_image:
#         return render(request, "recipient/add_dialog/add_photo.html", {})
#
#     # Strange to return a response like this.
#     # Apparently photo_crop view can return a response, a ResizeResult, or None.
#     response = photo_crop_view(request,
#                                some_image,
#                                "recipient/add_dialog/crop_photo.html",
#                                (250, 210),
#                                (250, 250),
#                                extra_data)
#
#     # Photo crop failed.
#     # Possibly because the path was not valid.
#     if response is None:
#         raise ImageCropException()
#
#     elif isinstance(response, ResizeResult):
#         # Handle the newly resized image and redirect back to dialog_direct
#         response.save()
#         request.GET = request.GET.copy()
#         request.GET["orig_fname"] = response.imagename
#         return dialog_direct(request, extra_data=extra_data)
#     else:
#         return response
#
# """ END ADD A RECIPIENT """
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ TAG DETAIL PAGE AKA RECIPIENT LABEL DETAIL PAGE """
# @page_template('mailbag/mailbag/tags/letters_single_col_topic_detail.html')
# def tag_detail(
#         request,
#         label_slug,
#         template='recipient/tag_detail.html',
#         letters_template='mailbag/mailbag/tags/letters_single_col_topic_detail.html',
#         extra_context=None):
#     """
#     Detail page for a given RecipientLabel.
#     Shows popular recipients, as well as either popular letters or all recipients
#     - Accepts URL parameters:
#         - 'show' : value is either 'letter' or 'recipients'
#         - 'show-recipients' :
#     - Context Contains:
#         - label : the RecipientLabel (tag) we are viewing
#         - labels : all RecipientLabels (tags) from the same type and category as 'label' and that have at least one recipient with a letter
#         - recipients_with_label : Any recipients that have have been tagged with any of the labels mentioned above
#         - popular_recipients : Top 10 recipients from recipients_with_label ordered by times tagged with label
#         - alphabetical_recipients : recipients_with_label reordered by name
#     """
#     # Why is this not in the labels app?
#     # Brad: good question
#     # from mailbag.models import Letter
#
#     show = request.GET.get("show", "letters")
#     show_recipients = request.GET.get("show-recipients", "")
#     label = get_object_or_404(RecipientLabel, slug=label_slug)
#     labels = label.get_all_children()
#     recipients_with_label = Recipient.objects.filter(recipienteditorlabel__label__in=labels).distinct()
#     popular_recipients = recipients_with_label.order_by('-rcptstats__num_letters')[:9]
#     alphabetical_recipients = recipients_with_label.order_by('name')
#     letters_with_label = Letter.objects.filter(recipient__in=recipients_with_label).order_by("-added_on")
#
#     recipients = Recipient.with_letters.all()
#     labels = RecipientLabel.objects.filter(label_type=label.label_type,
#                                            category=label.category,
#                                            recipienteditorlabel__recipient__in=recipients).distinct().select_related("category"
#                                                                                                                      ).order_by('category__slug', 'slug')
#
#     context = {
#         'popular_recipients': popular_recipients,
#         'alphabetical_recipients': alphabetical_recipients,
#         'label': label,
#         'letters': letters_with_label,
#         'letters_template': letters_template,
#         'show_recipients': show_recipients,
#         'show': show,
#         'labels': labels,
#     }
#
#     getvars = request.GET.copy()
#     if 'page' in getvars:
#         del getvars['page']
#     if len(getvars.keys()) > 0:
#         context['getvars'] = "&%s" % getvars.urlencode()
#     else:
#         context['getvars'] = ''
#
#     if extra_context is not None:
#         context.update(extra_context)
#
#     return render_to_response(
#         template,
#         context,
#         context_instance=RequestContext(request))
#
#
# """ TAG DETAIL PAGE: RELATED TAGS/LABELS """
# def labels(request, template='recipient/labels.html'):
#     """List all recipient labels to faciliate browsing"""
#     # No context needed; the template uses templatetags instead.
#     return render(request, template, {})
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT DETAIL PAGE """
# @page_template('mailbag/mailbag/tags/letters_single_col_recipient_detail.html')
# @page_template("mailbag/mailbag/tags/letters_single_col_recipient_detail.html", key="right_column_page")
# @page_template("mailbag/mailbag/tags/letters_ajax.html", key="most_recent_page")
# @page_template("mailbag/mailbag/tags/letters_ajax.html", key="most_recommended_page")
# def recipient_detail(
#         request,
#         recipient_id,
#         template='recipient/detail.html',
#         letters_template='mailbag/mailbag/tags/letters_single_col_recipient_detail.html',
#         extra_context=None):
#
#     try:
#         recipient = Recipient.objects.get(url=recipient_id)
#     except Recipient.DoesNotExist:
#         try:
#             id = long(recipient_id)
#         except (ValueError, TypeError):
#             id = -1
#
#         recipient = get_object_or_404(Recipient, pk=id)
#
#     labels = LetterLabel.objects.filter(
#             letterlabelstats__letter__recipient=recipient).annotate(
#             num_letters=Count('letterlabelstats__letter')).order_by(
#             '-num_letters')
#
#
#     """ RECIPIENT DETAIL PAGE: POPULAR RECIPIENTS FOOTER """
#     # A list of the most popular recipients related to a certiarea, like a recipient or category
#     # used to populate the recipient footer
#     MIN_NUM = 15
#     MAX_NUM = 15 # for now, no jquery scroll
#
#     '''
#     EXCLUDE_FILTERS = [Q(photo__isnull=True), Q(photo=''), Q(pk=recipient.pk)]
#
#     editor_labels = recipient.recipienteditorlabel_set.select_related('label')
#     popular_recipients = (Recipient.objects
#         .filter(recipienteditorlabel__label__in=[x.label for x in editor_labels])
#         .exclude(reduce(operator.or_, EXCLUDE_FILTERS))
#         .distinct()
#         .order_by('-rcptstats__num_letters3'))[0:MAX_NUM]
#
#     if len(popular_recipients) < MIN_NUM: # using len since qs needs to be evaluated regardless
#         if recipient.label_category:
#             difference = MIN_NUM - len(popular_recipients)
#             EXCLUDE_FILTERS.append(Q(pk__in=popular_recipients))
#             more_recipients = (recipient.label_category.recipient_set
#                 .exclude(reduce(operator.or_, EXCLUDE_FILTERS))
#                 .distinct()
#                 .order_by('-rcptstats__num_letters3'))[0:difference]
#             popular_recipients = itertools.chain(popular_recipients, more_recipients)
#     '''
#
#     EXCLUDE_FILTERS = [Q(recipient__photo__isnull=True), Q(recipient__photo=''), Q(recipient__pk=recipient.pk)]
#
#     editor_labels = [x.label for x in recipient.recipienteditorlabel_set.select_related('label')]
#
#     # Refactor to create base query  - most of this is the same. select related, ordering, excludes - 1
#     # Alternate query using RcptStats
#     #base_query = (RcptStats.objects.exclude(reduce(operator.or_, EXCLUDE_FILTERS))
#     popular_recipients = (RcptStats.objects
#         .filter(recipient__recipienteditorlabel__label__in=editor_labels)
#         .exclude(reduce(operator.or_, EXCLUDE_FILTERS))
#         .order_by("-num_letters3")
#         .select_related('recipient'))[:MAX_NUM]
#         # distinct() here causes error for too many columns in subquery
#
#     # expand search to all recipients in the category
#     if len(popular_recipients) < MIN_NUM:
#         if recipient.label_category: # sometimes, no label_category
#             EXCLUDE_FILTERS.append(Q(recipient__in=popular_recipients))
#             more_recipients = (RcptStats.objects
#                 .filter(recipient__label_category=recipient.label_category)
#                 .exclude(reduce(operator.or_, EXCLUDE_FILTERS))
#                 .order_by("-num_letters3")
#
#                 .select_related('recipient'))[:MIN_NUM - len(popular_recipients)]
#             popular_recipients = itertools.chain(popular_recipients, more_recipients)
#
#     popular_recipients = list(set(popular_recipients))
#     random.shuffle(popular_recipients)
#     popular_recipients = popular_recipients[0:5]
#     popular_recipients = [x.recipient for x in popular_recipients]
#
#     start = int(request.REQUEST.get('start', 0))
#     rows = int(request.REQUEST.get('rows', 10))
#     """ RECIPIENT DETAIL PAGE: VIEW BY LABEL, LOGIC FOR 2 COLUMN VS. 1 COLUMN """
#     # view by label (/?label=funny)
#     label = request.GET.get('label', '')
#     expand = request.GET.get('expand', '')
#
#     recommended_letters = recipient.recommended_letters
#     new_letters = recipient.new_letters
#
#     # Force view into a single column
#     force_single_column = False
#     show_filter_menu = False
#     columns = 1
#     letters = recommended_letters
#     letter_sorting = 'Most Recommended'
#     sort_key = ""
#
#     right_column_label = request.GET.get('right_column_label', '')
#     right_column_expand = request.GET.get('right_column_expand', '')
#     right_column_letter_sorting = "Most Recent"
#     right_column_letters = new_letters
#     right_column_sort_key = ""
#
#     # If this flag is set to false then show page in old design
#     foxtrot = request.GET.get('foxtrot', '')
#     if foxtrot == 'false' or foxtrot == 'False':
#         foxtrot = False
#     else:
#         foxtrot = True
#
#     # Decide on whether or not we should force one col
#     # One column is forced either when there are less than 13 letters in the
#     # most recommended column or when 4 most recent letters also contain letters
#     # that fall into the 4 most recommeneded letters, so there are duplicates
#     # at the top of the page.
#     a = [y.id for y in new_letters[:4]]
#     b = [z.id for z in recommended_letters[:4]]
#     if len([x for x in a if x in b]) > 0 or recommended_letters.count() < 13:
#         force_single_column = True
#
#     # Try to get letters for a label if possible.
#     # Otherwise, get all letters for the recipient, sorted based on expan
#     # If expand is not valid, return no letters.
#     if label:
#         try:
#             label = LetterLabel.objects.get(slug=label)
#         except LetterLabel.DoesNotExist:
#             pass
#         else:
#             letters = recommended_letters.filter(
#                     letterlabelstats__label=label
#                     ).order_by('-letterlabelstats__num')[start:rows]
#             letter_sorting = label.name
#             sort_key = 'label=%s' % label.slug
#     elif expand == 'recommended':
#         letters = recommended_letters
#         letter_sorting = 'Most Recommended'
#         sort_key = 'expand=recommended'
#     elif expand == 'recent':
#         letters = new_letters
#         letter_sorting = 'Most Recent'
#         sort_key = 'expand=recent'
#     # Show default page (recent/recommended)
#     else:
#         if force_single_column and not foxtrot:
#             letters = new_letters
#             letter_sorting = 'Most Recent'
#             sort_key = 'expand=recent'
#         else:
#             columns = 2
#             # letters = []
#             letters = recommended_letters
#             letter_sorting = 'Most Recommended'
#             sort_key = 'expand=recommended'
#
#     letters_count = letters.count()
#     if not force_single_column or force_single_column and letters_count >= 3:
#         show_filter_menu = True
#
#     # Same for the right column
#     if right_column_label:
#         try:
#             right_column_label = LetterLabel.objects.get(slug=right_column_label)
#         except LetterLabel.DoesNotExist:
#             pass
#         else:
#             right_column_letters = recommended_letters.filter(
#                     letterlabelstats__label=right_column_label
#                     ).order_by('-letterlabelstats__num')[start:rows]
#             right_column_letter_sorting = right_column_label.name
#             right_column_sort_key = 'right_column_label=%s' % right_column_label.slug
#     elif right_column_expand == 'recommended':
#         right_column_letters = recommended_letters
#         right_column_letter_sorting = 'Most Recommended'
#         right_column_sort_key = 'right_column_expand=recommended'
#     elif right_column_expand == 'recent':
#         right_column_letters = new_letters
#         right_column_letter_sorting = 'Most Recent'
#         right_column_sort_key = 'right_column_expand=recent'
#     # Show default page (recent/recommended)
#     else:
#         right_column_letters = new_letters
#         right_column_letter_sorting = 'Most Recent'
#         right_column_sort_key = 'right_column_expand=recent'
#
#     # Force single column for foxtrot
#     if foxtrot and letters_count < 4:
#         force_single_column = True
#         columns = 1
#         letters = new_letters
#         letter_sorting = 'Most Recent'
#         sort_key = 'expand=recent'
#     elif foxtrot and not force_single_column:
#         columns = 2
#
#     """ RECIPIENT DETAIL PAGE: FOLLOWED AUTHORS """
#     # If the current user is non anonymous, get their followed users
#     followed_profiles = None
#     if not request.user.is_anonymous():
#         followed_profiles = request.user.get_profile().profiles_im_following
#
#     """ RECIPIENT DETAIL PAGE: ANONYMOUS TOOL TIP """
#     # If this is the current anonymous users first time to the site (and this page), we will be
#     # displaying a tooltip to remind them that they can write letter anonymously
#     first_visit = False
#     if not 'first_visit' in request.session and request.user.is_anonymous():
#         first_visit = True
#         request.session['first_visit'] = False
#
#     getvars = request.GET.copy()
#     if len(getvars.keys()) > 0:
#         getvars = "&%s" % getvars.urlencode()
#     else:
#         getvars = ''
#
#     # Redefine letters in case of ajax request
#     key = request.GET.get('querystring_key', '')
#     if key == 'most_recent_page':
#         letters = new_letters
#     elif key == 'most_recommended_page':
#         letters = recommended_letters
#     elif key == 'right_column_page':
#         letters = right_column_letters
#
#     # Get popular mailbags for this recipient
#     initial_popular_mailbags = False
#     initial_popular_mailbags_count = False
#     if not request.is_ajax():
#         initial_popular_mailbags, initial_popular_mailbags_count = recipient_popular_mailbags_and_topics(request, recipient.id)
#
#     context = {
#         'recipient': recipient,
#         'rcpnt': recipient,
#         'popular_recipients': popular_recipients,
#         'initial_popular_mailbags': initial_popular_mailbags,
#         'initial_popular_mailbags_count': initial_popular_mailbags_count,
#         'followed_profiles': followed_profiles,
#         'key': key,
#
#         'label': label,
#         'labels': labels,
#         'letters': letters,
#         'letters_template': letters_template,
#
#         'show_filter_menu': show_filter_menu,
#         'letter_sorting': letter_sorting,
#         'sort_key': sort_key,
#         'force_single_column': force_single_column,
#         'columns': columns,
#         'first_visit': first_visit,
#
#         'right_column_expand': right_column_expand,
#         'right_column_letters': right_column_letters,
#         'right_column_label': right_column_label,
#         'right_column_letter_sorting': right_column_letter_sorting,
#         'right_column_sort_key': right_column_sort_key,
#     }
#
#     if extra_context is not None:
#         context.update(extra_context)
#
#     return render_to_response(
#         template,
#         context,
#         context_instance=RequestContext(request))
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# # This function is used to populate recipient's Popular topics section. It is
# # similar to `_popular_mailbags()` from `mailbags.py` (which is not optimized
# # for recipients), borrows code from it and returns data in the same format,
# # so it can be used by `homepage.popular_mailbags.js` script.
# #
# # Logic is described in #1086
# def recipient_popular_mailbags_and_topics(request, recipient_id):
#     # We only have 6 slots on the page now
#     LIMIT = 6
#     exclude_mailbag_ids = []
#     recipient = get_object_or_404(Recipient, pk=recipient_id)
#
#     # Get popular mailbags for given recipient. We do need no more than LIMIT
#     q = MailbagStats.objects.filter(mailbag__recipient=recipient.id).exclude(mailbag__is_default=True)
#     popular_mailbags_qs = [stat.mailbag for stat in q.order_by("-num_letters2", "-num_letters3", "-num_letters4")[:LIMIT]]
#     exclude_mailbag_ids.extend([item.pk for item in popular_mailbags_qs])
#
#     # Get popular topics for given recipient. We do need no more than LIMIT
#     popular_topics_qs = recipient.topicseed_set.all().exclude(mailbag__pk__in=exclude_mailbag_ids).exclude(is_default=True)
#     popular_topics_qs.order_by('-topicseedstats__num_letters_total2', '-topicseedstats__num_letters_total3', '-topicseedstats__num_letters_total4', '-topicseedstats__num_letters_total')[:LIMIT]
#
#     # Manually prepare an object for serialisation because sometimes
#     # get_absolute_url raises exceptions
#     def prepare(representative_object):
#         o = {
#             'id': representative_object.id,
#             'name': representative_object.normalize['name'],
#             'short_name': representative_object.normalize['short_name'],
#             'description': representative_object.desc,
#             'slug': representative_object.slug,
#             'photo_url': representative_object.thumbnail_popular_mailbags_recipient_page,
#             'type': representative_object.mtype,
#             'in': representative_object.channel.normalize['short_name'] if representative_object.channel is not None else '',
#             'in_url': representative_object.channel.normalize['url'] if representative_object.channel is not None else '',
#             'original': representative_object.original_name,
#             'original_id': representative_object.original_id,
#             'sort': representative_object.sort,
#             'count': representative_object.count,
#             'original_type': representative_object.original_type
#         }
#
#         try:
#             o['color'] = representative_object.channel.label_category.color
#         except AttributeError:
#             try:
#                 o['color'] = representative_object.channel.color
#             except AttributeError:
#                 pass
#         try:
#             o['avatar'] = representative_object.thumbnail_small
#         except:
#             pass
#         try:
#             o['url'] = representative_object.get_absolute_url()
#             return o
#         except:
#             return dict()
#
#     # If topic seed also has a mailbag associated with it under the recipient,
#     # show the mailbag in place of the topic seed
#     def get_object(instance):
#         if isinstance(instance, Mailbag):
#             obj = instance
#             # Try to get the most related topic channel name
#             related_topics = instance.topic_seed.through.objects.filter(mailbag=instance).order_by('-relevance')
#             if len(related_topics):
#                 tmp_channel = related_topics[0].topic_seed.normalize['channel']
#                 obj.channel = tmp_channel if tmp_channel.normalize['object'] is not None else instance.normalize['channel']
#             else:
#                 obj.channel = instance.normalize['channel']
#             obj.sort = instance.stats.num_letters2 + instance.stats.editor_weight
#             obj.count = instance.stats.num_letters
#             obj.original_id = instance.id
#             obj.original_name = instance.name
#             obj.original_type = "Mailbag"
#
#         elif isinstance(instance, TopicSeed):
#             related_mailbag = None
#             for mailbag in instance.mailbag_set.all():
#                 if mailbag.recipient.pk == recipient.pk:
#                     related_mailbag = mailbag
#             if related_mailbag:
#                 obj = related_mailbag
#             else:
#                 obj = instance
#             obj.sort = instance.stats.num_letters_total2 + instance.stats.editor_weight
#             obj.count = instance.stats.num_letters_total
#             obj.original_id = instance.id
#             obj.original_name = instance.name
#             obj.original_type = "TopicSeed"
#             obj.channel = instance.normalize['channel']
#
#         return obj
#
#     # Combine, dedupe and sort results before serializing
#     results = dedupe(sorted([get_object(obj) for obj in itertools.chain(popular_mailbags_qs, popular_topics_qs)],
#                             key=lambda x: x.sort, reverse=True))
#     results = results[:LIMIT]
#     results_count = len(results)
#
#     # Convert to json
#     jsonable = dict()
#     # `Event` here is a fake in order to utilize `homepage.popular_mailbags.js`
#     jsonable["event"] = [prepare(item) for item in results]
#     json = json.dumps(jsonable)
#     return json, results_count
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT DETAIL PAGE: LATEST OPEN LETTER BY THE RECIPIENT """
# def pr_latest_open_letter(request, rcpnt_id, mailbag_id=None):
#     """JSON view: return latest open letter written by a recipient.
#
#     DRY: Reuse the equivalent template tag.
#
#     """
#     from recipient.templatetags.recipienttags import pr_latest_open_letter as dry_call
#     rcpnt = get_object_or_404(Recipient, pk=rcpnt_id)
#     if mailbag_id:
#         mailbag = get_object_or_404(rcpnt.mailbag_set, pk=mailbag_id)
#     else:
#         mailbag = None
#     ctx = {'rcpnt_id':rcpnt.pk, 'rcpnt_name':rcpnt.name}
#     ctx2 = dry_call(rcpnt, mailbag)
#     letter = ctx2.get('letter', None)
#     if letter:
#         ctx.update({
#             'has_letter':True,
#             'body':letter.body,
#             # TODO: add other letter attributes here as needed by the AJAX view
#         })
#     else:
#         ctx['has_letter'] = False
#     mimetype, indent = get_json_mimetype_and_indent(request)
#     return HttpResponse(json.dumps(ctx, ensure_ascii=False, indent=indent), mimetype=mimetype)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT DETAIL PAGE: LATEST REPLIES BY THE RECIPIENT """
# def pr_latest_replies(request, rcpnt_id, mailbag_id=None, limit='20'):
#     """JSON view: return latest replies written by the given participating recipient.
#
#     DRY: Reuse the equivalent template tag.
#
#     """
#     from recipient.templatetags.recipienttags import pr_latest_replies as dry_call
#     rcpnt = get_object_or_404(Recipient, pk=rcpnt_id)
#     if mailbag_id:
#         mailbag = get_object_or_404(rcpnt.mailbag_set, pk=mailbag_id)
#     else:
#         mailbag = None
#     ctx = {'rcpnt_id':rcpnt.pk, 'rcpnt_name':rcpnt.name}
#     ctx2 = dry_call(rcpnt, mailbag, limit)
#     ctx['reply_count'] = ctx2['reply_count']
#     replies = ctx2.get('replies', None)
#     if replies:
#         ctx['has_replies'] = True
#         reply_list = []
#         for letter in replies:
#             ltr = {
#                 'to':letter.author_name,
#                 'body':letter.body,
#                 'reply':letter.pr_reply_body,
#                 # TODO: add other letter attributes here as needed by the AJAX view
#             }
#             reply_list.append(ltr)
#         ctx['replies'] = reply_list
#     else:
#         ctx['has_replies'] = False
#     mimetype, indent = get_json_mimetype_and_indent(request)
#     return HttpResponse(json.dumps(ctx, ensure_ascii=False, indent=indent), mimetype=mimetype)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT SEARCH RESULTS PAGE """
# def search(request, template='recipient/search_results.html'):
#     """Recipient search results.
#
#     Query parameters:
#         `q` - the search phrase (required)
#         `page` - page_number (default: 1)
#         `per_page` - number of rows per page (default: 10)
#
#     """
#     ctx = {}
#     query = request.REQUEST.get('q', u'')
#     if not query:
#         raise Http404(_(u"Provide a search parameter"))
#     page = int(request.REQUEST.get('page', 1))
#     per_page = int(request.REQUEST.get('per_page', _PER_PAGE))
#     ctx['q'] = query
#     words = query.split()
#     q = u"(%s)" % ' OR '.join(words)
#     params = dict(
#         q=q,
#         model='recipient__recipient',
#         is_seed=False,
#         sort=u'score desc,num_letters desc',
#         page=page,
#         per_page=per_page
#     )
#     paginator = SearchPaginator(params, request)
#     ctx['start_index'] = ((page - 1) * per_page) + 1
#     ctx['end_index'] = ctx['start_index'] + per_page - 1
#     if ctx['end_index'] > paginator.results.count:
#         ctx['end_index'] = paginator.results.count
#     ctx['paginator'] = paginator
#     ctx['raw_query'] = query
#     return render(request, template, ctx)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT SEARCH RESULTS USED BY GLOBAL SITE SEARCH WITH AUTOCOMPLETE """
# def primary_search(request):
#     """Search for recipients whose name begins with the given query string.
#     Return a JSON response.
#
#     This is used by the recipient autocomplete frontend module.
#
# Sample JSON result (/recipient/primary-search/?q=g):
#
# {
#     "results": [
#         {
#             "is_seed": false,
#             "name": "George Clooney",
#             "url": "/recipient/detail/4/",
#             "text": "George Clooney George Timothy Clooney",
#             "num_letters": 2,
#             "thumbnail": "/media/photos/2009-05-07/f510d343-ca29-4976-a40a-8ebe39f0c78e.jpg",
#             "label": null,
#             "alias": "George Timothy Clooney",
#             "birth_date": "1961-05-06",
#             "model": "recipient__recipient",
#             "id": "4",
#             "added_on": "2009-05-07"
#         },
#         {
#             "is_seed": true,
#             "name": "Google",
#             "url": "/recipient/detail/5/",
#             "text": "Google Google, Inc.",
#             "num_letters": 0,
#             "thumbnail": "/media/photos/2009-05-07/2bdaff19-1413-4818-9598-c363c61377cf.jpg",
#             "label": null,
#             "alias": "Google, Inc.",
#             "birth_date": "1998-09-07",
#             "model": "recipient__recipient",
#             "id": "5",
#             "added_on": "2009-05-07"
#         },
#         {
#             "is_seed": false,
#             "name": "Garry Kasparov",
#             "url": "/recipient/detail/20/",
#             "text": "Garry Kasparov Garrik Kimovich Weinstein",
#             "num_letters": 1,
#             "thumbnail": "/media/photos/2009-05-07/56ba94ab-72ab-45e0-a940-c8bec11244d4.jpg",
#             "label": null,
#             "alias": "Garrik Kimovich Weinstein",
#             "birth_date": "1963-04-13",
#             "model": "recipient__recipient",
#             "id": "20",
#             "added_on": "2009-05-07"
#         },
#         {
#             "is_seed": true,
#             "name": "Gata Kamsky",
#             "url": "/recipient/detail/21/",
#             "text": "Gata Kamsky",
#             "num_letters": 0,
#             "thumbnail": "/media/photos/2009-05-07/a42652f1-06b3-45ff-ba94-2a669f0d586a.jpg",
#             "label": null,
#             "alias": null,
#             "birth_date": "1974-06-02",
#             "model": "recipient__recipient",
#             "id": "21",
#             "added_on": "2009-05-07"
#         }
#     ],
#     "success": true
# }
#
# Sample Empty result (/recipient/primary-search/?q=x):
#
# {
#     "success": false
# }
#
#     """
#
#     query = request.REQUEST.get('q', u'')
#     if not query:
#         raise Http404(_(u"Provide a search parameter"))
#
#     recipient_params = dict(
#         q=u'name:%s*' % query.title(), # name begins with query
#         model='recipient__recipient',
#         is_seed=False,
#         # sort=u'score desc,num_letters desc', # sorts don't work with wild card queries
#     )
#     recipient_results = solr.select(recipient_params)
#
#     topic_params = dict(
#         q='name:%s*' % query.title(),
#         model='mailbag__topicseed',
#         hidden=False,
#         )
#     topic_results = solr.select(topic_params)
#
#
#     if recipient_results.count or topic_results.count:
#         docs = []
#         # convert each result doc into a JSON serializable dictionary:
#         for d in recipient_results.documents:
#             doc = {}
#             is_seed = d.fields.get('is_seed', False)
#             if is_seed and not is_seed.value: # exclude seed recipients
#                 for key, value in d.fields.iteritems():
#                     if key not in ('bio', 'site_id'):
#                         v = value.value
#                         if isinstance(v, date) or isinstance(v, datetime):
#                             v = unicode(v)
#                         doc[key] = v
#                 if not doc.get('url'):
#                     doc['url'] = reverse("recipient_detail", kwargs={"recipient_id":doc["id"]})
#                 docs.append(doc)
#
#         for d in topic_results.documents:
#             doc = {}
#             hidden = d.fields.get('hidden', False)
#             if hidden and not hidden.value:
#                 for key, value in d.fields.iteritems():
#                     v = value.value
#                     if key == 'name':
#                         v += ''
#                     if isinstance(v, date) or isinstance(v, datetime):
#                         v = unicode(v)
#                     doc[key] = v
#                     doc['url'] = reverse("global_search") + "?q=%s" % d.fields['name'].value
#                 docs.append(doc)
#
#         # Convert the relative URLs to absolute URLs to deal with the news land category page since sometimes people
#         # will be searching from a subdomain
#         for doc in docs:
#             if 'url' in doc:
#                 doc['url'] = "http://"+Site.objects.get_current().domain + doc['url']
#
#         docs = sorted(docs, key=lambda d: d['name'])
#
#         ctx = {
#             'results': docs,
#             'success': True,
#             }
#     else:
#         ctx = {
#             'success':False
#             }
#
#     mimetype, indent = get_json_mimetype_and_indent(request)
#     return HttpResponse(json.dumps(ctx, ensure_ascii=False, indent=indent), mimetype=mimetype)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def search_and_redirect(request):
#     """Search for recipients by primary and alternate names.
#
#     If more than one primary or alternate names match, redirect user to
#     the global search. If only one primary or alternate name matches, redirect
#     user to the recipient's page directly.
#
#     This is used by the recipient autocomplete frontend module.
#
#     """
#     query = request.REQUEST.get('q', u'')
#     if not query:
#         raise Http404(_(u"Provide a search parameter"))
#     global_search_url = u"%s?q=%s*" % (reverse("global_search"), query)
#     params = dict(
#         q=u'name:%s*' % query.title(), # name starts with q
#         model='recipient__recipient',
#         is_seed=False,
#         # sort=u'score desc,num_letters desc', # sorts don't work with wild card queries
#     )
#     results = solr.select(params)
#     if results.count > 1:
#         # more than one result; redirect to global search
#         return HttpResponseRedirect(global_search_url)
#     if results.count == 1:
#         # get matching recipient id and redirect straight to the recipient's main page
#         rcpnt_id = results.documents[0].fields["id"].value
#         return HttpResponseRedirect(reverse("recipient_detail", kwargs={"recipient_id":rcpnt_id}))
#     # Primary name was not a match; check secondary names
#     params['q'] = u'alias:%s*' % query.title() # secondary name starts with q
#     results = solr.select(params)
#     if results.count > 1:
#         # more than one result; redirect to global search
#         return HttpResponseRedirect(global_search_url)
#     if results.count == 1:
#         # get matching recipient id and redirect straight to the recipient's main page
#         rcpnt_id = results.documents[0].fields["id"].value
#         return HttpResponseRedirect(reverse("recipient_detail", kwargs={"recipient_id":rcpnt_id}))
#     # No primary or secondary matches; redirect to global search
#     return HttpResponseRedirect(global_search_url)
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def recipient_autocomplete(request):
#     """
#     Ajax method that returns a list of recipient names; used with jquery.autocomplete.js
#     """
#
#     query = request.GET.get("q", "")
#
#     if query == "":
#        raise Http404(_(u"Must provide a value to query on"))
#
#     recipients = Recipient.objects.filter(name__istartswith=query).order_by("name")
#     recipient_text = u"\n".join([e.name for e in recipients])
#     return HttpResponse(recipient_text, mimetype="text/plain")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ RECIPIENT SALUTATIONS """
# # Used in the tool tip on compose to suggest how to start the open letter
# def salutations(request, rcpnt_id):
#     """
#     Ajax method that returns a list of saluations for addressing this recipient,
#     used with jquery.autocomplete.js
#
#     You can get all salutations for a user by providing the query "q=_all".
#
#     This should be changed to use json
#     """
#     query = request.GET.get("q", "")
#     if query == "":
#        raise Http404(_(u"Must provide a value to query on"))
#     recipient = get_object_or_404(Recipient, pk=rcpnt_id)
#     if query == "_all":
#         recipient_salutations = RecipientSalutation.objects.filter(recipient=rcpnt_id).order_by('-count')
#     else:
#         recipient_salutations = recipient_salutations.filter(recipient=rcpnt_id, salutation__icontains=query).order_by('-count')
#     if len(recipient_salutations) < 10:
#         count = 10 - len(recipient_salutations)
#         generic_salutations =  GenericSalutation.objects.all()
#         if query == "_all":
#             generic_salutations =  GenericSalutation.objects.all()[:count]
#         else:
#             generic_salutations = GenericSalutation.objects.filter(value__istartswith=query)[:count]
#     salutations = [e.salutation_with_comma for e in recipient_salutations] + [e.value_by_recipient(recipient) for e in generic_salutations]
#     return HttpResponse(u"\n".join(salutations), mimetype="text/plain")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ LIST OF SIGNOFFS (e.g. Bye) FOR THE OPEN LETTERS """
# # Used in compose dialog to close open letters
# def signOffs(request):
#     """
#     Ajax method that returns a list of sign-offs for addressing this recipient,
#     used with jquery.autocomplete.js
#     """
#     query = request.GET.get("q", "")
#
#     if query == "":
#        raise Http404(_(u"Must provide a value to query on"))
#
#
#     signoffs = SignOff.objects.filter(value__istartswith=query).order_by('value').values()
#     text = u"\n".join(["%s," % e['value'].rstrip() for e in signoffs])
#     return HttpResponse(text, mimetype="text/plain")
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def valid_name(request, rcpnt_name):
#     rs = Recipient.objects.filter(name=rcpnt_name)
#     return HttpResponse(json.dumps({"valid": bool(rs)}),  mimetype='application/json')
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# """ ADD A PHOTO DIALOG """
# @csrf_exempt
# def recipient_add_photo(request):
#     '''
#     add a photo to a recipient that was created without a photo
#     '''
#     extra_data = json.loads(request.REQUEST.get('final_information', '{}'))
#     ctx = { "response_info": json.dumps(extra_data) }
#
#     web_img = request.GET.get('img', '').strip()
#     file_img = request.FILES.get('img')
#     if not (web_img or file_img):
#         return render(request, "recipient/recipient_add_photo.html", ctx)
#
#     extra_data.update({'photo_credit': request.GET.get('photo_credit', ''),
#                        'photo_explanation': request.GET.get('photo_explanation', ''),
#                        'fairuse_reason': request.GET.get('fairuse_reason', ''),
#                        'fairuse_webpage': request.GET.get('fairuse_webpage', ''),
#                        })
#     response = photo_crop_view(request,
#                                web_img or file_img,
#                               "recipient/recipient_crop_photo.html",
#                                (250, 210),
#                                (250, 250),
#                                extra_data,
#                                allow_resize=False)
#
#     if response is None:
#         # TODO: Failure to crop, skip to finish!
#         request.GET = request.GET.copy()
#         request.GET['errors'] = "We couldn't download the suggested image from its url.  Please close this dialog and try again."
#         return recipient_photo_error(request)
#
#     elif isinstance(response, ResizeResult):
#         response.save()
#         request.GET = request.GET.copy()
#         request.GET["orig_fname"] = response.imagename
#         # TODO: Go to finish page
#         return recipient_add_photo_finish(request)
#
#     else:
#         return response
#===============================================================================

#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def recipient_add_photo_finish(request):
#     """
#     the photo has been uploaded and cropped, lets add it to the recipient
#     """
#     extra_data = {}
#     extra_data.update(json.loads(request.REQUEST.get('final_information', '{}')))
#
#     if 'crop' in extra_data:
#         photo = photo_crop_success(Recipient, 'photo', extra_data['crop']['orig_fname'], (250, 210), crop_size=(250, 250), crop_params=extra_data['crop'])
#     else:
#         photo = None
#
#     try:
#         recipient_id = extra_data['target_id']
#         recipient = Recipient.objects.get(id=recipient_id)
#
#         if photo:
#             credit = RecipientPhotoCredit()
#             credit.image_credit = request.GET.get('photo_credit', '')
#             credit.source_explaination = request.GET.get('photo_explanation')
#             credit.fairuse_reason = request.GET.get('fairuse_reason')
#             credit.website_source = request.GET.get('fairuse_webpage')
#             credit.save()
#
#             recipient.photo_credit = credit
#             recipient.photo = photo
#             recipient.save()
#
#             success = True
#         else:
#             success = False
#
#     except Recipient.DoesNotExist:
#         success = False
#         pass
#
#     retval = {'success': success}
#     mimetype, indent = get_json_mimetype_and_indent(request)
#     return HttpResponse(json.dumps(retval, ensure_ascii=False, indent=indent), mimetype=mimetype)
#===============================================================================


#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def recipient_photo_error(request, template='recipient/recipient_photo_error.html'):
#     """
#     An error has occurred, so show the error page.
#     """
#     ctx = {'errors': request.GET.get('errors', '')}
#     return render(request, template, ctx)
#===============================================================================


#splitcodeprocess 01.21.2019 Maksim Kislitsyn: Comment don't using code
#===============================================================================
# def yahoo_image_search(request, query):
#     """
#     Perform yahoo boss image search.
#     """
#
#     url = "http://yboss.yahooapis.com/ysearch/images"
#     params = {
#         'oauth_version': "1.0",
#         'oauth_nonce': oauth2.generate_nonce(),
#         'oauth_timestamp': int(time.time()),
#         'q': quote(query),
#         'dimensions': 'medium',
#         'format': 'json',
#     }
#
#     consumer = oauth2.Consumer(key=settings.YAHOO_CONSUMER_KEY, secret=settings.YAHOO_CONSUMER_SECRET)
#     req = oauth2.Request(method="GET", url=url, parameters=params)
#     signature_method = oauth2.SignatureMethod_HMAC_SHA1()
#     req.sign_request(signature_method, consumer, None)
#
#     try:
#         response = urllib2.urlopen(req.to_url())
#         if response.getcode() == 200:
#             results = json.loads(response.read())['bossresponse']['images']['results']
#
#             # really simple, but dumb pagination
#             i = 0
#             page = 1
#             for result in results:
#                 result["page"] = page
#                 i += 1
#                 if i == 8:
#                     i = 0
#                     page += 1
#
#             results_html = render_to_string('recipient/yahoo_image_search_results.html',{'results':results,'request':request,'pages': range(page),})
#             response_data = {
#                 'results_html': results_html,
#                 'response': 1,
#             }
#         else:
#             response_data = {'response': 0}
#     except urllib2.URLError as err:
#         response_data = {'response': 0}
#     except KeyError:
#         response_data = {'response': 0}
#
#     return HttpResponse(json.dumps(response_data), mimetype='text/html')
#===============================================================================

#facebook key
def get_facebook_key(request):
    from django.conf import settings
    _list = []
    _list.append(getattr(settings, 'FB_STATIC_KEY_1', ''))
    return HttpResponse(json.dumps(_list), content_type="application/json")

# Tooltip API Data


def get_data_by_twitter_id(request, twitter_id):
    """
    function for getting data for a twitter that can be displayed
    in a tool tip for an object with either attribute. we use this in our
    chrome extension to display bio information on a social commenter.
    """
    from django_apps.recipient.entities import get_image_for_recipient
    from django_apps.recipient.editorData import CATEGORIES_FIELDS

    data = {}
    recipient = lookup_for_valid_recipient_by_tw_account(twitter_id)
    wikiid = None
    if recipient:
        data['id'] = recipient.id
        img = get_image_for_recipient({}, recipient)
        if img and img.strip() and recipient.id <= 2250000:
            data['image'] = img.strip()
        else:
            if recipient.images.exists():
                data['image'] = list(recipient.images.values())[0]['url']
        if recipient.related_companies.exists():
            data['related_companies'] = [c['name']
                                         for c in list(recipient.related_companies.values())]
        if recipient.nationalities.exists():
            data['nationalities'] = [c['nationality']
                                     for c in list(recipient.nationalities.values())]
        if recipient.tags.exists():
            data['tags'] = [tag.value.value for tag in recipient.tags.all()]
        if recipient.related_people.exists():
            data['related_people'] = [c['name']
                                      for c in list(recipient.related_people.values())]
        if recipient.date_of_birth:
            try:
                data['date_of_birth'] = recipient.date_of_birth.strftime(
                    '%B %d, %Y')
            except:
                pass
        if recipient.short_desc:
            data['short_desc'] = recipient.short_desc

        wikiid = recipient.wikiid

    entry = TWITTER_CATEGORIES_MAP.get(twitter_id.lower())
    if entry:
        data['category'] = entry[CATEGORIES_FIELDS.category]
        data['subcategory'] = entry[CATEGORIES_FIELDS.subcategory]
        if not wikiid:
            wikiid = entry.get(CATEGORIES_FIELDS.wiki)

    if not entry or (not data['category'] or not data['subcategory']):
        entry = additional_categorization_map.get(twitter_id.lower())
        if entry:
            data['category'] = entry[0]
            data['subcategory'] = entry[1]
        else:
            if "@"+twitter_id.lower() in dynamic_categorization_conditional_wordslist['sports_news_handles']:
                data['category'] = 'News'
                data['subcategory'] = 'Digital'
            elif "@"+twitter_id.lower() in dynamic_categorization_conditional_wordslist['news_handles']:
                data['category'] = 'News'
                data['subcategory'] = 'News Outlet'
            elif "@"+twitter_id.lower() in dynamic_categorization_conditional_wordslist['sports_mediamembers_handles']:
                data['category'] = 'News'
                data['subcategory'] = 'Media Member'

    wiki_ids = []
    if wikiid:
        wiki_ids = wiki_permutations(wikiid)

    data['csv_data'] = []

    for section in CSV_SECTIONS:
        valid_rows = get_csv_rows_by_wiki_ids_and_twitter_id(
            section['section'], wiki_ids, twitter_id)
        if not valid_rows:
            continue

        section_data = []

        for field in section['fields']:
            field_data_list = []
            for valid_row in valid_rows:
                if not valid_row.get(field['data_col']):
                    continue

                if 'link_col' in field and valid_row.get(field['link_col']):
                    field_data = {'link': valid_row.get(field['link_col']),
                                  'data': valid_row.get(field['data_col'])}
                else:
                    field_data = {'data': valid_row.get(field['data_col'])}

                field_data_list.append(field_data)

            if not field_data_list:
                continue
            item = {'label': field['label'], 'fields': field_data_list}

            section_data.append(item)

        if section_data:
            data['csv_data'] += section_data

    try:
        conn = sqlite3.connect(
            f"/home/ec2-user/sd/sd/django_apps/recipient/scripts/UsernameRelatedCurations/username_related_curations.sqlite")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT * from links_data where user_account = '{twitter_id}'""")
        if (str(request.GET.get("related_curations")) == "True" or str(request.GET.get("related_curations")) == "true"):
            RECORDS_CURATED = [dict(x) for x in cursor.fetchall()]
            UPDATED_RECORDS = []
            for singlerec in RECORDS_CURATED:
                if (singlerec["user_account"] == "" or
                   (singlerec["user_account"] and len(singlerec["user_account"]) < 3)):
                    pass
                elif (singlerec["link_title"] == "" or
                      (singlerec["link_title"] and len(singlerec["link_title"]) < 3)):
                    pass
                else:
                    UPDATED_RECORDS.append(singlerec)
            data['related_curations'] = UPDATED_RECORDS
            # data['related_curations'].append(str(twitter_id))
            # data['related_curations'].append(str(cursor))
    except Exception as e:
        data['related_curations'] = "ERROR:"+str(e)

    return HttpResponse(json.dumps(data), content_type="application/json")


def get_twitter_ids(request):
    """
    function for returning a full list of twitter ids that is used in Chrome extension
    help on determine if we should place a tip icon for the twitter.
    """
    twitter_ids = SocialAccount.objects.filter(
        service__exact=SocialAccount.TWITTER).values_list('value')
    data = set(el[0] for el in twitter_ids)
    if USE_CSV_FOR_VALIDRECIPIENTS:
        data.update(list(TWITTER_CATEGORIES_MAP.keys()))
        # additional categorization
        data.update(list(additional_categorization_map.keys()))
        # dynamic usernames
        dynamic_names = []
        dynamic_names += [name.replace('@', '')
                          for name in dynamic_categorization_conditional_wordslist['sports_news_handles']]
        dynamic_names += [name.replace('@', '')
                          for name in dynamic_categorization_conditional_wordslist['news_handles']]
        dynamic_names += [name.replace('@', '')
                          for name in dynamic_categorization_conditional_wordslist['sports_mediamembers_handles']]

        data.update(dynamic_names)

    for section in CSV_SECTIONS:
        pattern = 'csv_cache_{}_twitter_*'.format(section)
        data.update(key[len(pattern)-1:] for key in csv_cache.keys(pattern))

    return HttpResponse(json.dumps(list(data)), content_type="application/json")


#splitcodeprocess 01.22.2019 Maksim Kislitsyn: move get_job_result from website.view
############  Anton Ershov  Start  June 21, 2017 ###############
@csrf_exempt
def get_job_result(request):
    if request.method == 'POST':
        try:
            job_id = request.POST.get('job_id', '')
            link_pk = request.POST.get('link_id', 0)
            main_task = request.POST.get('main_task', False)
            raw_data = {}
            if link_pk:
                try:
                    link = Link.objects.get(pk=link_pk)
                    raw_data = json.loads(link.jsons.raw_social_data)
                except Link.DoesNotExist:
                    # nothing to do, trying to get data from celery
                    pass
            if job_id:
                if job_id in raw_data and not main_task:
                    response = {
                        'status': 'ready',
                        'data': raw_data[job_id],
                        'job_name': ''
                    }
                    return HttpResponse(json.dumps(response))
                job_result = celery_app.AsyncResult(job_id)
                if job_result.ready():
                    response = {
                        'status': 'ready',
                        'data': raw_data if main_task else job_result.get(),
                        'job_name': job_result.name,
                    }
                else:
                    response = {
                        'status': job_result.status,
                        'job_name': job_result.name,
                    }
                return HttpResponse(json.dumps(response))

            # we handle multiple jobs polling in same view
            jobs = request.POST.get('jobs', '').split(',')
            if jobs:
                response = {
                    'results': []
                }
                for job_id in jobs:
                    if job_id in raw_data:
                        result = {
                            'status': 'ready',
                            'data': raw_data[job_id],
                            'job_id': job_id,
                            'job_name': '',
                        }
                        response['results'].append(result)
                        continue
                    job_result = celery_app.AsyncResult(job_id)
                    if job_result.ready():
                        try:
                            result = {
                                'status': 'ready',
                                'data': job_result.get(),
                                'job_id': job_id,
                                'job_name': job_result.name,
                            }
                        except Exception as ex:
                            result = {
                                'status': 'error',
                                'error': str(ex),
                                'job_id': job_id,
                                'job_name': job_result.name,
                                'stacktrace': traceback.format_exc(),
                            }
                        response['results'].append(result)

                    else:
                        result = {
                            'status': job_result.status,
                            'job_id': job_id,
                            'job_name': job_result.name,
                        }
                        response['results'].append(result)
                return HttpResponse(json.dumps(response))

        except Exception as ex:
            response = {
                'status': 'error',
                'error': str(ex),
                #splitcodeprocess 02.22.2019 Maksim Kislitsyn: raw_post_data was renamed to  body
                'income_data': request.body.decode('utf-8'),
                #===============================================================
                # 'income_data': request.raw_post_data,
                #===============================================================
                'stacktrace': traceback.format_exc()
            }

        return HttpResponse(json.dumps(response))
    return HttpResponse(json.dumps({'error': 'Method not allowed'}), status=405)
############  Anton Ershov  End  June 21, 2017 ###############

#splitcodeprocess 01.22.2019 Maksim Kislitsyn: move revoke_job from website.view
#splitcodeprocess 02.28.2019 Maksim Kislitsyn: add @csrf_exempt


@csrf_exempt
def revoke_job(request):
    if request.method == 'POST' and request.is_ajax():
        try:
            job_id = request.POST.get('job_id', '')
            terminate = request.POST.get('terminate', True)
            revoke(job_id, terminate=terminate)
            response = {
                'status': 'ready',
            }
        except Exception as ex:
            response = {
                'status': 'error',
                'error': str(ex),
                'income_data': request.body.decode('utf-8'),
            }

        return HttpResponse(json.dumps(response))
    return HttpResponse('Ajax request required')

#splitcodeprocess 01.22.2019 Maksim Kislitsyn: move robots from website.view


def robots(request):
    #splitcodeprocess 02.04.2019 Maksim Kislitsyn: mimetype was removed from django HttpResponse, need to use content_type
    return HttpResponse("User-agent: twitter\nUser-agent: twitterbot \nDisallow:\n\nUser-agent: * \nDisallow: /*", content_type='text/plain')
    #===========================================================================
    # return HttpResponse("User-agent: twitter\nUser-agent: twitterbot \nDisallow:\n\nUser-agent: * \nDisallow: /*", mimetype='text/plain')
    #===========================================================================
    #return HttpResponse("User-agent: * \nDisallow: /*", mimetype='text/plain')
    #forproduction    return HttpResponse("User-agent: * \nDisallow: /home/*\nDisallow: /nytechday/*\nDisallow: /captcha/*\nDisallow: /media/ui/images/townhall/*", mimetype='text/plain')

#splitcodeprocess 01.22.2019 Maksim Kislitsyn: move after_twitter_authentication from website.view


def after_twitter_authentication(request):
    """
    After logging in with twitter, check if the user has a site_identity
    set in his user profile. If it doesn't have any set, then set his
    site identity to his twitter's first name + space + twitter's last name
    """
    next_path = request.GET.get('next', '/hello/')
    from_extension = True if "extension" in next_path else False

    if request.user:
        try:
            user_profile = UserProfile.objects.get(
                user__username=request.user.username)
        except UserProfile.DoesNotExist:
            return HttpResponseRedirect('/')
        if user_profile.site_identity.strip() == '':
            user_profile.site_identity = '%s %s' % (
                request.user.first_name, request.user.last_name)
            user_profile.save()

    # now establish a home timeline and reading_list sessin for the user if they don't already have one and fetch metadata
    # for the reading list.
    if not request.user.is_anonymous and request.user.encrypted_social_auth.filter(provider='twitter'):
        try:
            if from_extension:
                oauth_tw = request.user.encrypted_social_auth.filter(provider='twitter')[
                    0]
                tw_oauth_token = oauth_tw.extra_data['access_token']
                session_key_home = 'home_timeline_' + \
                    tw_oauth_token.get('screen_name')
                if not session_key_home in request.session:
                    session_key_reading_list = 'reading_list_' + \
                        tw_oauth_token.get('screen_name')
                    if not session_key_reading_list in request.session:
                        home_timeline_tweets, tweets_for_reading_list = home_timeline(
                            tw_oauth_token, [], add_to_reading_list=True)
                        request.session[session_key_home] = home_timeline_tweets
                        request.session[session_key_reading_list] = tweets_for_reading_list
                        r = update_reading_list_metadata(
                            request, send_back_new_list=False)
        except Exception as ex:
            tracing_logger.error(traceback.format_exc())
            tracing_logger.error(str(ex))

    path = urljoin('/', next_path)
    return HttpResponseRedirect(path)


def publisher_demo(request):
    """
    use single-file chrome extension to download a copy of a publisher's page html
    then embed custom widget on it with button to demo for them experience.
    """
    site = request.GET.get('s', None)
    if site:
        template = "website/publisher_demos/" + site + ".html"
        context = {}
        return render(request, template, context=context)


def twitter_collection_page_certain_link(request, link_id, template='recipient/tw_collection_share_page.html'):
    embed = request.GET.get('embed', False)
    if embed:
        template = 'recipient/tw_collection_embed_page.html'
    collection_url = None
    link = get_object_or_404(Link, pk=link_id)
    if not link.jsons.raw_social_data_api:
        raise Http404('No data in link.')
    elif request.method == 'GET':
        link_info = get_link_details_from_cache(link_id)
        collection_url = link_info.get('collection_url', '')
        # todo: the lines below in getting from raw_api_json we could do without if we save some of needed fields in context in redis.
        # it might lower data transfer (network in and out) but then we'd have to weigh that against redis memory space of saving more data.
        raw_api_json = json.loads(link.jsons.raw_social_data_api)
        # get a thumbnail image for the story by iterating through related news
        if not link.image_url:
            raw_json = json.loads(link.jsons.raw_social_data)
            for news_story in raw_json['related']:
                if "twitter.com" not in news_story['link']:
                    if news_story.get('image_url'):
                        link.image_url = news_story.get('image_url')
                        tracing_logger.debug(
                            'photooooooooooooooooooooooooooooooooooooooooooooooooooooooo 0')
                        tracing_logger.debug(link.image_url)
                        link.save()
                        break
        # get a thumbnail image for the story by iterating through tweets that have shared a link
        if not link.image_url:
            tweets = []
            if raw_json.get("tweets_clusterization_media_job_id"):
               final_clusterization_job_id = raw_json["tweets_clusterization_media_job_id"]
               if raw_json.get(final_clusterization_job_id, {}).get('tweets', []):
                   tweets = raw_json[final_clusterization_job_id].get(
                       'tweets', [])
            for tweet in tweets:
                if (tweet.get('is_eligible') or tweet.get('is_valid')) and tweet.get('is_verified') and tweet.get('url_metadata', {}).get('image'):
                    link.image_url = tweet.get('url_metadata', {}).get('image')[
                        0].get('url', '')
                    if link.image_url:
                        tracing_logger.debug(
                            'photoooooooooooooooooooooooooooooooooooooooooooooooooooooo 1')
                        tracing_logger.debug(link.image_url)
                        link.save()
                        break
            # get a thumbnail image for the story by iterating through tweets that have shared a photo
            if not link.image_url:
                unverified_photos = []
                for tweet in tweets:
                    if (tweet.get('is_eligible') or tweet.get('is_valid')) and tweet.get(TW_HAS_MEDIA_FIELD) and tweet[TW_HAS_MEDIA_FIELD][1] == 'photo':
                       # data looks like this = src="<div id="tweetimage" style="background-image:url(https://pbs.twimg.com/media/EtorDMjXMAAU8vd.jpg)"> </div>"
                       # extract url in two steps
                       img_url = tweet['tw_media_html']['full_mode'].split(
                           "image:url(")[1]
                       img_url = img_url.split(")")[0]
                       if tweet.get('is_verified'):
                           try:
                               link.image_url = get_cropped_image_view(img_url)
                               tracing_logger.debug(
                                   'bradddddddddddddddddddddddddddddddddddddddddddddddddddddd 2')
                               tracing_logger.debug(link.image_url)
                               link.save()
                               break
                           except:
                               pass
                       else:
                           unverified_photos.append(img_url)
        if not link.image_url:
            if unverified_photos:
                try:
                    link.image_url = get_cropped_image_view(
                        unverified_photos[0])
                    tracing_logger.debug(
                        'bradddddddddddddddddddddddddddddddddddddddddddddddddddddd 3')
                    tracing_logger.debug(link.image_url)
                except:
                    pass
            else:
                link.image_url = "https://theconversation.social/static/home/images/twitter-512-opacity.png"
            link.save()
        if not collection_url:
            collection_url = raw_api_json.get('collection_url', '')
        if not collection_url:
            # TODO: this is duplicate code from demo_api2 -- make it into one function
            public = sorted(raw_api_json['general_public']['tweets'],
                            key=lambda obj: obj['overall_relevance'], reverse=False)
            media = sorted(raw_api_json['media']['tweets'],
                           key=lambda obj: obj['overall_relevance'], reverse=False)
            notable = sorted(raw_api_json['notable_people_and_orgs']['tweets'],
                             key=lambda obj: obj['overall_relevance'], reverse=False)
            people_involved = raw_api_json['public_figures_involved']['tweets']
            b_people = [t for t in media if t["media_category"]
                        != "news_organization"]
            b_orgs = [t for t in media if t["media_category"]
                      == "news_organization"]
            pub_staff = raw_api_json['media']['pub_staff']
            # order of the ids matter here.  first added will show up last in the collection.
            collection_tweet_ids = [tweet['id'] for tweet in (
                b_orgs + public + b_people + notable + people_involved + pub_staff)]
            # create the curation
            if collection_tweet_ids:
                if not collection_url:
                    # Description lenght must be no more 160 and name no more 30?
                    # get collection_name from request
                    collection_name = "The Best of the Conversation"
                    collection_description = raw_api_json.get('article_summary', {}).get(
                        'title', '')[:158]  # get collection_description from request
                    tw_oauth_token = None
                    collection = create_collection(tw_oauth_token, str(
                        collection_name), str(collection_description), collection_tweet_ids)
                    collection_id = collection['response']['timeline_id']
                    for key, value in collection.get('objects', {}).get('timelines').items():
                        raw_api_json['collection_url'] = value.get(
                            'collection_url')
                        request.session[value.get(
                            'collection_url')+"_last_tweet_ids"] = collection_tweet_ids
                        # add the collection_url to our json api
                        _save_job_results_to_link(link_id, {'collection_url': value.get(
                            'collection_url')}, "", job_name=None, only_api=True,)
                        collection_url = value.get('collection_url')
                        save_link_info_to_cache(link_id, collection_url=value.get('collection_url'),
                                                collection_id=collection_id, collection_tweet_ids_list=collection_tweet_ids)
                        create_collection_post_save_thread = threading.Thread(target=create_collection_with_sleep, args=(
                            tw_oauth_token, "a", "b", collection_tweet_ids, collection_tweet_ids, collection_id))
                        create_collection_post_save_thread.start()

        context = {
            "link_id": link_id,
            "collection_url": collection_url + "?l_id=" + link_id,
            "article_image": link.image_url if link.image_url else "https://theconversation.social/static/home/images/twitter-512-opacity.png",
            "article_url": link.url,
            "article_title": raw_api_json.get('article_summary', {}).get('title', 'Social Reactions'),
            "article_description": raw_api_json.get('article_summary', {}).get('meta_desc', 'What people are saying about this topic'),
            "created_on": link.created_on,
            "last_fetch": link.last_fetch,
        }
        return render(request, template, context=context)

    else:
        raise Http404('Wrong method.')


def video_results_page(request, link_id, template='recipient/video_results.html'):
    """
    a page that shows related youtube videos for a certain link id
    """
    NUM_VIDEOS_SHOW = 8
    # do this since slicing at 0 will include an extra 1.
    NUM_VIDEOS_SHOW = NUM_VIDEOS_SHOW - 1
    yt_q = None
    youtube_ids = None
    link = get_object_or_404(Link, pk=link_id)
    if not link.jsons.raw_social_data_api:
        return render(request, template_name=template, context={'header': [], 'rows': []})
    elif request.method == 'GET':
        # get data from redis to check if we have video ids already generated or at least a query
        link_info = get_link_details_from_cache(link_id)
        youtube_ids = link_info.get('yt_ids_list', None)
        until_date = link_info.get('until_date', None)
        since_date = link_info.get('since_date', None)
        # if not youtube ids, we will try to get the query from redis so we can search yt and then retrieve the ids
        if not youtube_ids:
            yt_q = link_info.get('yt_q', None)
            # if no query exists
            if not yt_q:
                return render(request, template_name=template, context={'header': [], 'rows': []})
            # otherwise, get the results from yt
            ### important todo -- if we have no video results, and redis has logged that, then we probably
            ### should not retry fetch_youtube_videos and just return no results
            youtube_results = fetch_youtube_videos(
                yt_q, pubBefore=until_date, pubAfter=since_date)[:NUM_VIDEOS_SHOW]
            #return HttpResponse(content(youtube_results))
            #return HttpResponse(content=(v['id'] for v in youtube_results))
            # now parse them into results and save them in redis for future use, so we don't have to re-do query again
            youtube_ids = [v['id'] for v in youtube_results]
            save_link_info_to_cache(link_id, yt_ids_list=youtube_ids)
            #return HttpResponse(content=youtube_ids)
            if not youtube_ids:
                return render(request, template_name=template, context={'header': [], 'rows': []})
        #return HttpResponse(content=youtube_ids)
        # now serve it into a web page. here we are doing a two column page,
        # making a dict like this for each video, in a list for the row [{'1': some-video-id},{'2': some-video-id}]
        context = {}
        template_name = template
        context['header'] = []
        context['rows'] = []
        row = {}
        columns_num = 2  # fill out a two column table
        counter = 0
        for id in youtube_ids:
            counter += 1
            if counter <= columns_num:
                row['{0}'.format(counter)] = id
            else:
                counter = 1
                row = {}
                row['{0}'.format(counter)] = id
            # row has been filed, add to rows list
            if counter == columns_num:
                context['rows'].append(row)
        # add unfilled final row to rows list
        if counter < columns_num:
            context['rows'].append(row)
        return render(request, template_name, context=context)
    else:
        raise Http404('Wrong method.')

#analytics map data / states


def get_states_data(request):
    _file = open("django_apps/recipient/csv-lists/analytics_map.json", "r")
    return HttpResponse(_file.read(), content_type="application/json")


def youtube_videos_raw(request):
    """
    for examining raw response to yt search queries
    """
    query = request.GET.get('q')
    if request.GET.get('q') == None:
        return HttpResponse(status=404, content="Not Found")
    else:
        try:
            #Extract the Query and pass it to the function that fetches the videos
            #The parameters to be passed are searchquery, language, region,safesearch, searchtype,embeddable, pubbefore, pubafter,maxresult
            #searchquery is mandatory requirement
            result = fetch_youtube_videos(searchquery=query)

            #If everythin is Okay,search results will be stored in results
            return HttpResponse(status=200, content=result)
        except Exception as ex:
            return HttpResponse(status=500, content=str(ex))


def get_tweet_info(request):
    """
    takes ?tweet_id=XXXXX in url
    get info about a tweet (collection_url for it, title of link it maps to).  returns dict with link_id, collection_url, title
    """
    tweet_id = request.GET.get('tw_id')
    result = get_tw_details_from_cache(tweet_id)

    return HttpResponse(json.dumps(result))


def get_mult_tweets_info(request):
    """
    takes ?tweet_id=XXXXX,YYYYYY,ZZZZZZ in url
    get info about multiple tweets (collection_url for it, title of link it maps to). returns dict with keys based on
    the tweet id that have a value of a dict storing the tweet_id's link_id it maps to, collection_url, title
    """
    tweet_ids = request.GET.get('tw_ids').split(',')
    tweet_ids = list(set(tweet_ids))  # dedupe just in case
    result = get_multiple_tweets_details_from_cache(tweet_ids)

    return HttpResponse(json.dumps(result))


def add_editorially_selected_tweet_ids(request):
    """
    only show tweets selected by an editor / moderator for a link
    """
    pass


def put_offtopic_to_tweet_ids(request):
    """
    takes ?tweet_id=XXXXX,YYYYYY,ZZZZZZ in url

    takes 'url' param and 'link_id' param as well

    allows person who is enabled moderator of that domain to delete tweets from the curation.

    """

    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    tweet_ids = request.GET.get('tw_ids', '')
    if tweet_ids:
       tweet_ids = tweet_ids.split(',')
    else:
        tweet_ids = []

    youtube_ids = request.GET.get('yt_ids', '')
    if youtube_ids:
        youtube_ids = youtube_ids.split(',')
    else:
        youtube_ids = []

    podcast_ids = request.GET.get('pod_ids', '')
    if podcast_ids:
        podcast_ids = podcast_ids.split(',')
    else:
        podcast_ids = []

    admin_mod_abilities = False
    original = False
    just_status = True
    link_object = None
    create_new_link = False
    url = data.get('url', '').strip()
    link_id = data.get('link_id', '').strip()

    if url and not link_id:
        url = unquote(url)

        # check if the account has moderator capabilities
        try:
            if request.user.is_staff:
               admin_mod_abilities = True
            elif not request.user.is_anonymous and request.user.profile and request.user.profile.allowed_domains:
                allowed_domains = request.user.profile.allowed_domains.split(
                    ',')
                allowed_domains = [d.strip() for d in allowed_domains]
                article_url_domain = get_domain_from_url(url)
                for d in allowed_domains:
                    if d == article_url_domain:
                        admin_mod_abilities = True
                        break
        except:
            pass

        if not admin_mod_abilities:
            return HttpResponse(json.dumps({'error': 'You do not have permission to make changes to curations for this URL'}))
        try:
            response, send_response, link_object = search_post_api_method(
                url, False, just_status, link_object, create_new_link)
        except:
            return HttpResponse(json.dumps({'error': 'Cannot find a link in the DB for this url'}))
        if link_object:
            link_id = link_object.id
    if link_id:
        if tweet_ids:
            result = {
                'map_tweet_ids_to_category_lists':
                {
                    'ineligible': tweet_ids
                }
            }
            _save_job_results_to_link(
                link_id, result, '', "user-initiated-offtopic")
            # update twitter collection
            link_info = get_link_details_from_cache(link_id)
            if link_info.get('collection_id') and tweet_ids:
                # todo untested -- import     tw_oauth_token = _get_twitter_account(request.user) to get the auth_token
                #and pass along in create_collection call
                create_collection(tweets_to_delete=tweet_ids,
                                  collection_id=link_info['collection_id'])

        if youtube_ids:
            _save_job_results_to_link(link_id, {'youtube_ids': youtube_ids},
                                      '', "user-initiated-youtube-offtopic")
        if podcast_ids:
            _save_job_results_to_link(link_id, {'podcast_ids': podcast_ids},
                                      '', "user-initiated-podcasts-offtopic")
        return HttpResponse(json.dumps({'deleted_tweets': tweet_ids, 'deleted_youtube_videos': youtube_ids,
                                        'deleted_podcast_eps': podcast_ids, 'on_url': url, 'link_id': link_id}))


def documentation_widget(request):
    return render(request, "registration/extension_demo/widget_on_article/widget-documentation.html")


def put_wrong_is_eligible(request):
    """
    takes ?eligible_wrong=X or ?ineligible_wrong=X or ?offtopic_wrong=X in url
    takes 'link_id' param
    allows person who is enabled moderator of that domain to mark eligible wrong, ineligible wrong and offtopic wrong tweets from the curation.
    # here is the original function which is in progress to finish todo -- https://paste.ee/p/ugIgi#uPtHehUd6r2GF533CqmwzwaKWNALKf73
    """

    if request.method == 'GET':
        data = request.GET
    elif request.method == 'POST':
        data = request.POST

    eligible_wrong = request.GET.get('eligible_wrong', '')
    ineligible_wrong = request.GET.get('ineligible_wrong', '')
    offtopic_wrong = request.GET.get('offtopic_wrong', '')

    if (eligible_wrong):
        tweet_ids = eligible_wrong

    if (ineligible_wrong):
        tweet_ids = ineligible_wrong

    if (offtopic_wrong):
        tweet_ids = offtopic_wrong

    link_id = data.get('link_id', '').strip()


def gallery_creator(request):
    return render(request, "recipient/gallery-creator.html")

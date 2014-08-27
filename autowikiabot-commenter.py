# -*- coding: utf-8 -*-

import praw, time, datetime, re, urllib, urllib2, pickle, pyimgur, os, traceback, wikia, string, socket, sys, collections
#from nsfw import getnsfw
from util import success, warn, log, fail, special, bluelog
from bs4 import BeautifulSoup
from HTMLParser import HTMLParser

WIKI_URL = 'wikia.com/wiki'
### Uncomment to debug
#import logging
#logging.basicConfig(level=logging.DEBUG)

### Set root directory to script directory
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

def find_link(body):
    begin_index = body.find("http://")
    for index, char in enumerate(body[begin_index:]):
        if char in (" ", ")"):
            end_index = index + begin_index
            break
    else:
        end_index = begin_index + index
    link = body[begin_index: end_index + 1]
    return link

def find_sub_wikia(link):
    # Just after http://, maybe should be more explicit here
    start_index = link.find("//") + 2
    end_index = link.find(".")
    if wikia.LANG:
        start_index = end_index
        end_index = link.find(".", start_index + 1)
    return link[start_index:end_index]

###Load data
def load_data():
  global banned_users
  global badsubs
  global root_only_subs
  global summon_only_subs
  global imgur_client_id
  global banned_users_page
  global badsubs_page
  global root_only_subs_page
  global summon_only_subs_page
  imgur_client_id = datafile_lines[2].strip()
  banned_users_page = r.get_wiki_page('autowikiabot','userblacklist')
  badsubs_page = r.get_wiki_page('autowikiabot','excludedsubs')
  root_only_subs_page = r.get_wiki_page('autowikiabot','rootonlysubs')
  summon_only_subs_page = r.get_wiki_page('autowikiabot','summononlysubs')
  try:
    banned_users = banned_users_page.content_md.strip().split()
    badsubs = badsubs_page.content_md.strip().split()
    root_only_subs = root_only_subs_page.content_md.strip().split()
    summon_only_subs = summon_only_subs_page.content_md.strip().split()
    success("DATA LOADED")
  except Exception as e:
    #traceback.print_exc()
    fail("DATA LOAD FAILED: %s"%e)
    exit()

def save_changing_variables(editsummary):
  ##Save badsubs
  global badsubs
  badsubs = list(set(badsubs))
  badsubs.sort(reverse=True)
  c_badsubs = ""
  for item in badsubs:
    c_badsubs = "    "+item+'\n'+c_badsubs
  r.edit_wiki_page('autowikiabot','excludedsubs',c_badsubs,editsummary)
  ##Save root_only_subs
  global root_only_subs
  root_only_subs = list(set(root_only_subs))
  root_only_subs.sort(reverse=True)
  c_root_only_subs = ""
  for item in root_only_subs:
    c_root_only_subs = "    "+item+'\n'+c_root_only_subs
  r.edit_wiki_page('autowikiabot','rootonlysubs',c_root_only_subs,editsummary)
  ##Save summon_only_subs
  global summon_only_subs
  summon_only_subs = list(set(summon_only_subs))
  summon_only_subs.sort(reverse=True)
  c_summon_only_subs = ""
  for item in summon_only_subs:
    c_summon_only_subs = "    "+item+'\n'+c_summon_only_subs
  r.edit_wiki_page('autowikiabot','summononlysubs',c_summon_only_subs,editsummary)


  success("DATA SAVED")

with open ('datafile.inf', 'r') as myfile:
  datafile_lines=myfile.readlines()

### Login
r = praw.Reddit("autowikiabot by /u/timidger at /r/autowikiabot")
USERNAME = datafile_lines[0].strip()
PASSWORD = datafile_lines[1].strip()
Trying = True
while Trying:
        try:
                r.login(USERNAME, PASSWORD)
                success("LOGGED IN")
                Trying = False
        except praw.errors.InvalidUserPass:
                fail("WRONG USERNAME OR PASSWORD")
                exit()
        except Exception as e:
          fail("%s"%e)
          time.sleep(5)

def is_summon_chain(post):
  if not post.is_root:
    parent_comment_id = post.parent_id
    parent_comment = r.get_info(thing_id=parent_comment_id)
    if parent_comment.author != None and str(parent_comment.author.name) == 'autowikiabot':
      return True
    else:
      return False
  else:
    return False

def comment_limit_reached(post):
  global submissioncount
  count_of_this = int(float(submissioncount[str(post.submission.id)]))
  if count_of_this > 4 and not (str(post.subreddit) == 'autowikiabotdelreq' or str(post.subreddit) == 'autowikiabot' or str(post.subreddit) == 'todayilearned'):
    return True
  else:
    return False

def is_already_done(post):
  done = False
  numofr = 0
  try:
    repliesarray = post.replies
    numofr = len(list(repliesarray))
  except:
    pass
  if numofr != 0:
    for repl in post.replies:
      if repl.author != None and (repl.author.name == 'autowikiabot' or repl.author.name == 'Text_Reader_Bot'):
        warn("%s IS ALREADY DONE"%post.id)
        done = True
        continue
  if done:
    return True
  else:
    return False

def post_reply(reply,post):
  global badsubs
  global submissioncount
  global totalposted
  # This is a quick hack to fix the double list issue (git issue #12)
  # Please find the actual source of this bug, and delete this hack
  # It removes any sentences that are posted more than once
  lines = []
  for line in reply.split("\n"):
    if line not in lines:
      lines.append(line)
  reply = '\n'.join(lines)
  try:
    reply = "#####&#009;\n\n######&#009;\n\n####&#009;\n"+reply+"\n\n^Parent ^commenter ^can [^toggle ^NSFW](http://www.np.reddit.com/message/compose?to=autowikiabot&subject=AutoWikibot NSFW toggle&message=%2Btoggle-nsfw+____id____) ^or[](#or) [^delete](http://www.np.reddit.com/message/compose?to=autowikiabot&subject=AutoWikibot Deletion&message=%2Bdelete+____id____)^. ^Will ^also ^delete ^on ^comment ^score ^of ^-1 ^or ^less. ^| [^(FAQs)](http://www.np.reddit.com/r/autowikiabot/wiki/index) ^|  [^Source](https://github.com/Timidger/autowikiabot-py)\n ^(Please note this bot is in testing. Any help would be greatly appreciated, even if it is just a bug report! Please checkout the) [^source ^code](https://github.com/Timidger/autowikiabot-py) ^(to submit bugs)"
    a = post.reply('[#placeholder-awb]Comment is being processed... It will be automatically replaced by new text within a minute or will be deleted if that fails.')
    postsuccess = r.get_info(thing_id='t1_'+str(a.id)).edit(reply.replace('____id____',str(a.id)))
    if not postsuccess:
      raise Exception ('reply unsuccessful')
    totalposted = totalposted + 1
    submissioncount[str(post.submission.id)]+=1
    success("[OK] #%s "%totalposted)
    return True
  except Exception as e:
    warn("REPLY FAILED: %s @ %s"%(e,post.subreddit))
    if str(e) == '(TOO_LONG) `this is too long (max: 15000.0)` on field `text`':
      a.delete()
    elif str(e) == '403 Client Error: Forbidden' and str(post.subreddit) not in badsubs:
      badsubs = badsubs_page.content_md.strip().split()
      badsubs.append(str(post.subreddit))
      editsummary = 'added '+str(post.subreddit)
      save_changing_variables(editsummary)
    else:
      fail(e)
      a.delete()
    return False

def filterpass(post):
  global summary_call
  global has_link
  global mod_switch
  global badsubs
  global r
  if (post.author.name == USERNAME) or post.author.name in banned_users:
    return False
  summary_call = re.search(r'wikiabot.\s*wh.{1,3}(\'s|\s+is|\s+are|\s+was)\s+(an\s+|a\s+|the\s+|)(.*?)$',post.body.lower()) or re.search(r'wikiabot.\s*tell\s.{1,23}\sabout\s+(an\s+|a\s+|the\s+|)(.*?)$',post.body.lower()) or re.search("\?\-.*\-\?",post.body.lower())
  has_link = any(string in post.body for string in [WIKI_URL])
  mod_switch = re.search(r'wikiabot moderator switch: summon only: on',post.body.lower()) or re.search(r'wikiabot moderator switch: summon only: off',post.body.lower()) or re.search(r'wikiabot moderator switch: root only: on',post.body.lower()) or re.search(r'wikiabot moderator switch: root only: off',post.body.lower())
  if has_link or summary_call or mod_switch:
    if re.search(r"&gt;", post.body) and not summary_call and not re.search(r"autowikiabot-welcome-token", post.body.lower()):
      return False
    elif re.search(r"wikia.com/wiki/.*wikia.com/wiki/", post.body, re.DOTALL):
      return False
    elif str(post.subreddit) in badsubs and not mod_switch:
      return False
    elif any(string in post.body for string in ['/wiki/File:', '/wiki/List_of', '/wiki/User:', '/wiki/Template:', '/wiki/Category:', '/wiki/Wikia:', '/wiki/Talk:']):
      return False
    elif str(post.subreddit) in root_only_subs and not post.is_root and not mod_switch:
      return False
    elif str(post.subreddit) in summon_only_subs and not summary_call and not mod_switch:
      return False
    if is_summon_chain(post):
      warn('SKIPPED CHAINED REPLY')
      return False
    elif is_already_done(post):
      return False
    elif comment_limit_reached(post):
      try:
        title = "COMMENT LIMIT " + "/r/"+str(post.subreddit)
        suburl = str(post.submission.short_link)
        r.submit('acini',title,url=suburl, raise_captcha_exception=True)
      except:
        pass
      return False
    else:
      return True

def get_url_string(post):
  try:
    after_split = post.body.split(WIKI_URL)[1]
    for e in ['\n', ' ']:
      after_split = after_split.split(e)[0]
    if after_split.endswith(')') and not re.search(r'\(',after_split):
      after_split = after_split.split(')')[0]
    if re.search(r'\)',after_split) and not re.search(r'\(',after_split):
      after_split = after_split.split(')')[0]
    return after_split
  except:
    pass

def process_summary_call(post):
  #special("__________________________________________________")
  #special("SUMMARY CALL: %s"%post.id)
  wikia = find_link(body)
  replacedbody = post.body.lower().replace('wikiabot','___uawb___wikiabot')
  if re.search(r'wikiabot.\s*tell\s.{1,23}\sabout\s+(an\s+|a\s+|the\s+|)(.*?)$',replacedbody):
    post_body = re.sub(r'wikiabot.\s*tell\s.{1,23}\sabout\s+(an\s+|a\s+|the\s+|)(.*?)$',r'\2',replacedbody).split('___uawb___')[1].split('.')[0].split('?')[0]
    term = post_body.strip()
  elif re.search(r'wikiabot.\s*wh.{1,3}(\'s|\s+is|\s+are|\s+was)\s+(an\s+|a\s+|the\s+|)(.*?)$',replacedbody):
    post_body = re.sub(r'wikiabot.\s*wh.{1,3}(\'s|\s+is|\s+are|\s+was)\s+(an\s+|a\s+|the\s+|)(.*?)$',r'\3',replacedbody).split('___uawb___')[1].split('.')[0].split('?')[0]
    term = post_body.strip()
  elif re.search("\?\-.*\-\?",replacedbody):
    term = re.search("\?\-.*\-\?",post.body.lower()).group(0).strip('?').strip('-').strip()

  special("SUMMARY CALL: %s @ %s"%(filter(lambda x: x in string.printable, term),post.id))
  if term.lower().strip() == 'love':
    #post_reply('*Baby don\'t hurt me! Now seriously, stop asking me about love so many times! O.o What were we discussing about in this thread again?*',post)
    return(False,False)
  #if term.lower().strip() == 'wikiabot':
    #post_reply('*Me! I know me.*',post)
    return(False,False)
  if term.lower().strip() == 'reddit':
    #post_reply('*This place. It feels like home.*',post)
    return(False,False)
  if term.strip().__len__() < 2 or term == None:
    log("EMPTY TERM")
    return(False,False)
  try:
    title = wikia.page(sub_wikia, term,).title
    # If it is the main page, don't try to summarise it
    if re.search("[M,m]ain_[P,p]age", title) or re.search("[W,w]iki", title):
      return (False, False)
    if title.lower() == term:
      bit_comment_start = ""
    elif title.lower() != term:
      try:
        discard = wikia.page(sub_wikia, term,redirect=False).title
      except Exception as e:
        if re.search('resulted in a redirect',str(e)):
          bit_comment_start = "*\"" + term.strip() + "\" redirects to* "
    else:
      bit_comment_start = "*Nearest match for* ***" + term.strip() + "*** *is* "
    if re.search(r'#',title):
      url = wikia.page(sub_wikia, title.split('#')[0],).url
      sectionurl =  url + "#" + title.split('#')[1]
      comment = "*Nearest match for* ***" + term.strip() + "*** *is the section ["+title.split('#')[1]+"]("+sectionurl.replace(')','\)')+") in article ["+title.split('#')[0]+"]("+url+").*\n\n---\n\n"
      post_reply(comment,post)
      log("RELEVANT SECTION SUGGESTED: %s"%filter(lambda x: x in string.printable, title))
      return (False,False)
    url_string = title
    log("INTERPRETATION: %s"%filter(lambda x: x in string.printable, title))
    return (url_string,bit_comment_start)
  except Exception as e:
    if bool(re.search('.*may refer to:.*',filter(lambda x: x in string.printable, str(e)))):
      deflist = ">Definitions for few of those terms:"
      for idx, val in enumerate(filter(lambda x: x in string.printable, str(e)).split('may refer to: \n')[1].split('\n')):
        deflist = deflist + "\n\n>1. **"+val.strip()+"**: "+ wikia.summary(sub_wikia, val,sentences=1)
        if idx > 3:
          break
      summary = "*Oops,* ***"+term.strip()+"*** *landed me on a disambiguation page.*\n\n---\n\n"+deflist+"\n\n---\n\n"
      log("ASKING FOR DISAMBIGUATION")
    else:
      log("INTERPRETATION FAIL: %s"%filter(lambda x: x in string.printable, term))
      try:
        terms = "\""+term+"\""
        suggesttitle = str(wikia.search(sub_wikia, terms,results=1)[0])
        log("SUGGESTING: %s"%filter(lambda x: x in string.printable, suggesttitle))
        if suggesttitle.lower() == term:
          bit_comment_start = ""
        else:
          bit_comment_start = "*Nearest match for* ***" + term.strip() + "*** *is* "
        if str(suggesttitle).endswith(')') and not re.search('\(',str(suggesttitle)):
          suggesttitle = suggesttitle[0:--(suggesttitle.__len__()-1)]
        return (str(suggesttitle),bit_comment_start)
      except:
        trialtitle = wikia.page(sub_wikia, term,).title
        if trialtitle.lower() == term:
          bit_comment_start = ""
        else:
          bit_comment_start = "*Nearest match for* ***" + term.strip() + "*** *is* "
        log("TRIAL SUGGESTION: %s"%filter(lambda x: x in string.printable, trialtitle))
        if str(trialtitle).endswith(')') and not re.search('\(',str(trialtitle)):
          trialtitle = trialtitle[0:--(trialtitle.__len__()-1)]
        return (str(trialtitle),bit_comment_start)
    post_reply(summary,post)
    return (False,False)

def clean_soup(soup):
  while soup.table:
    discard = soup.table.extract()
  while soup.find(id='coordinates'):
    discard = soup.find(id='coordinates').extract()
  while soup.find("strong", { "class" : "error mw-ext-cite-error" }):
    discard = soup.find("strong", { "class" : "error mw-ext-cite-error" }).extract()
  while soup.find("sup", { "class" : "reference" }):
    discard = soup.find("sup", { "class" : "reference" }).extract()
  while soup.find("span", { "class" : "t_nihongo_help noprint" }):
    discard = soup.find("span", { "class" : "t_nihongo_help noprint" }).extract()
  while soup.find("span", { "class" : "sortkey" }):
    discard = soup.find("span", { "class" : "sortkey" }).extract()

  for tag in soup:
    if tag.name == 'a' and tag.has_attr('href'):
      rep = "["+tag.text+"]("+tag['href']+")"
      discard = tag.replace_with(rep)
  return soup

def reddify(html):
  global has_list
  if re.search('&lt;li&gt;',html):
    has_list = True
  else:
    has_list = False
  html = html.replace('&lt;b&gt;', '__')
  html = html.replace('&lt;/b&gt;', '__')
  html = html.replace('&lt;i&gt;', '*')
  html = html.replace('&lt;/i&gt;', '*')
  if '__*' in html and '*__' in html:
    html = html.replace('__*', '___')
    html = html.replace('*__', '___')
  html = re.sub('&lt;sup&gt;','^',html)
  html = re.sub('&lt;sup.*?&gt;',' ',html)
  html = html.replace('&lt;/sup&gt;','')
  html = html.replace('&lt;dt&gt;','&lt;p&gt;')
  html = html.replace('&lt;/dt&gt;','&lt;/p&gt;')
  html = html.replace('&lt;ul&gt;','&lt;p&gt;')
  html = html.replace('&lt;/ul&gt;','&lt;/p&gt;')
  html = html.replace('&lt;ol&gt;','&lt;p&gt;')
  html = html.replace('&lt;/ol&gt;','&lt;/p&gt;')
  html = html.replace('&lt;dd&gt;','&lt;p&gt;>')
  html = html.replace('&lt;/dd&gt;','&lt;/p&gt; ')
  html = html.replace('&lt;li&gt;','&lt;p&gt;* ')
  html = html.replace('&lt;/li&gt;','&lt;/p&gt;')
  html = html.replace('&lt;blockquote&gt;','&lt;p&gt;>')
  html = html.replace('&lt;/blockquote&gt;','&lt;/p&gt; ')
  return html

def strip_wiki(wiki):
  wiki = re.sub('\[[0-9]\][^(]','',wiki)
  wiki = re.sub('\[[0-9][0-9]\][^(]','',wiki)
  wiki = re.sub('\[[0-9][0-9][0-9]\][^(]','',wiki)
  wiki = re.sub("\( listen\)", '', wiki)
  return wiki

def truncate(data, length):
  if data.__len__() > length:
    log("TEXT CUT AT %s CHARACTERS"%length)
    data = data[0:length]+" ... \n`(Truncated at "+str(length)+" characters)`"
    return data
  else:
    return data

def process_brackets_links(string):
  string = ("%s)"%string)
  string = string.replace("\\", "")
  return string

def process_brackets_syntax(string):
  string = string.replace("\\", "")
  string = ("%s\)"%string)
  return string

### declare variables
load_data()
im = pyimgur.Imgur(imgur_client_id)
global pagepropsdata
submissioncount = collections.Counter()
lastload = int(float(time.strftime("%s")))
has_list = False
totalposted = 0

while True:
  try:
    #comments = r.get_comments("all",limit = 1000)
    #for post in comments:
    for post in praw.helpers.comment_stream(r,str(sys.argv[1]), limit = None, verbosity=0):
      link = find_link(post.body)
      ### Dirty timer hack
      now = int(float(time.strftime("%s")))
      diff = now - lastload
      if diff > 899:
        banned_users = banned_users_page.content_md.strip().split()
        bluelog("BANNED USER LIST RENEWED")
        save_changing_variables('scheduled dump')
        lastload = now

      if filterpass(post):
        if mod_switch:
          try:
            mod_switch_summon_on = re.search(r'wikiabot moderator switch: summon only: on',post.body.lower())
            mod_switch_summon_off = re.search(r'wikiabot moderator switch: summon only: off',post.body.lower())
            mod_switch_root_on = re.search(r'wikiabot moderator switch: root only: on',post.body.lower())
            mod_switch_root_off = re.search(r'wikiabot moderator switch: root only: off',post.body.lower())

            mods = r.get_moderators(str(post.subreddit))
            is_mod = False
            for idx in range(0,len(mods)):
              if mods[idx].name == post.author.name:
                is_mod = True
                break
            if is_mod:
              if mod_switch_summon_on:
                if str(post.subreddit) in summon_only_subs:
                  comment = "*Summon only feature is already* ***ON*** *in /r/"+str(post.subreddit)+"*\n\n---\n\n"
                else:
                  summon_only_subs.append(str(post.subreddit))
                  if str(post.subreddit) in badsubs:
                    badsubs.remove(str(post.subreddit))
                  editsummary = 'added '+str(post.subreddit)+', reason:mod_switch_summon_on'
                  save_changing_variables(editsummary)
                  comment = "*Summon only feature switched* ***ON*** *for /r/"+str(post.subreddit)+"*\n\n---\n\n"
              elif mod_switch_summon_off:
                if str(post.subreddit) not in summon_only_subs:
                  comment = "*Summon only feature is already* ***OFF*** *in /r/"+str(post.subreddit)+"*\n\n---\n\n"
                else:
                  badsubs = badsubs_page.content_md.strip().split()
                  summon_only_subs.remove(str(post.subreddit))
                  if str(post.subreddit) in badsubs:
                    badsubs.remove(str(post.subreddit))
                  editsummary = 'removed '+str(post.subreddit)+', reason:mod_switch_summon_off'
                  save_changing_variables(editsummary)
                  comment = "*Summon only feature switched* ***OFF*** *for /r/"+str(post.subreddit)+"*\n\n---\n\n"
              elif mod_switch_root_on:
                if str(post.subreddit) in root_only_subs:
                  comment = "*Root only feature is already* ***ON*** *in /r/"+str(post.subreddit)+"*\n\n---\n\n"
                else:
                  root_only_subs.append(str(post.subreddit))
                  if str(post.subreddit) in badsubs:
                    badsubs.remove(str(post.subreddit))
                  editsummary = 'added '+str(post.subreddit)+', reason:mod_switch_root_on'
                  save_changing_variables(editsummary)
                  comment = "*Root only feature switched* ***ON*** *for /r/"+str(post.subreddit)+"*\n\n---\n\n"
              elif mod_switch_root_off:
                if str(post.subreddit) not in root_only_subs:
                  comment = "*Root only feature is already* ***OFF*** *in /r/"+str(post.subreddit)+"*\n\n---\n\n"
                else:
                  badsubs = badsubs_page.content_md.strip().split()
                  root_only_subs.remove(str(post.subreddit))
                  if str(post.subreddit) in badsubs:
                    badsubs.remove(str(post.subreddit))
                  editsummary = 'removed '+str(post.subreddit)+', reason:mod_switch_root_off'
                  save_changing_variables(editsummary)
                  comment = "*Root only feature switched* ***OFF*** *for /r/"+str(post.subreddit)+"*\n\n---\n\n"
              else:
                comment = False

              if comment:
                a = post_reply(comment,post)
                title = "MODSWITCH: %s"%str(post.subreddit)
                subtext = "/u/"+str(post.author.name)+": @ [comment]("+post.permalink+")\n\n"+str(post.body)+"\n\n---\n\n"+comment
                r.submit('acini',title,text=subtext, raise_captcha_exception=True)
              if a:
                special("MODSWITCH: %s @ %s"%(comment.replace('*',''),post.id))
              else:
                fail("MODSWITCH REPLY FAILED: %s @ %s"%(comment,post.id))
                title = "MODSWITCH REPLY FAILED: %s"%str(post.subreddit)
                subtext = "/u/"+str(post.author.name)+": @ [comment]("+post.permalink+")\n\n"+str(post.body)+"\n\n---\n\n"+comment
                r.submit('acini',title,text=subtext, raise_captcha_exception=True)
            else:
              if post.subreddit not in badsubs:
                comment = "*Moderator switches can only be switched ON and OFF by moderators of this subreddit.*\n\n*If you want specific feature turned ON or OFF, [ask the moderators](http://www.np.reddit.com/message/compose?to=%2Fr%2F"+str(post.subreddit)+") and provide them with [this link](http://www.np.reddit.com/r/autowikiabot/wiki/modfaqs).*\n\n---\n\n"
                post_reply(comment,post)
          except Exception as e:
            title = "MODSWITCH FAILURE !!: %s"%str(post.subreddit)
            traceback.print_exc()
            subtext = "/u/"+str(post.author.name)+": @ [comment]("+post.permalink+")\n\n"+str(post.body)+"\n\n---\n\n"+str(e)
            r.submit('acini',title,text=subtext, raise_captcha_exception=True)
          continue
        elif has_link:
          url_string = get_url_string(post)
          log("__________________________________________________")
          log("LINK TRIGGER: %s"%post.id)
          bit_comment_start = ""
        else:
          try:
            url_string = ""
            url_string, bit_comment_start = process_summary_call(post)
            if url_string == False:
              continue
            url_string = str(url_string)
          except Exception as e:
            if bool(re.search('.*may refer to:.*',filter(lambda x: x in string.printable, str(e)))):
              deflist = ">Definitions for few of those terms:"
              for idx, val in enumerate(filter(lambda x: x in string.printable, str(e)).split('may refer to: \n')[1].split('\n')):
                deflist = deflist + "\n\n>1. **"+val.strip()+"**: "+ wikia.summary(sub_wikia, val,sentences=1)
                if idx > 3:
                  break
              summary = "*Oops,* ***"+url_string.strip()+"*** *landed me on a disambiguation page.*\n\n---\n\n"+deflist+"\n\n---\n\n"
              log("ASKING FOR DISAMBIGUATION")
              post_reply(summary,post)
              continue
        if not url_string:
          continue
        article_name_terminal = None
        sub_wikia = find_sub_wikia(link)
        # Screw it, I'm not digging through uncommented regexs
        url_string = url_string.replace("/", "")
        base_wikia_url = "https://" + sub_wikia + ".wikia.com/"
        is_section = False
        ### check for subheading in url string, process if present
        if re.search(r"#",url_string) and not summary_call:
          pagenameraw = url_string.split('#')[0]
          pagename = pagenameraw.replace(')','\)')
          pagename = pagename.replace('(','\(')
          pagename = pagename.strip().replace('.','%')
          pagename = urllib.unquote(str(pagename))
          sectionnameraw = url_string.split('#')[1]
          sectionname = sectionnameraw.replace('(','\(')
          sectionname = sectionname.replace(')','\)')
          sectionname = sectionname.strip().replace('.','%')
          sectionname = urllib.unquote(str(sectionname))
          try:
            url = (base_wikia_url+"api.php?action=parse&page="+pagename.encode('utf-8','ignore')+"&format=xml&prop=sections")
            socket.setdefaulttimeout(30)
            slsoup = BeautifulSoup(urllib2.urlopen(url).read())
            if slsoup.find_all('s').__len__() == 0:
              raise Exception("no sections found")
            for s in slsoup.find_all('s'):
              if s['anchor'] == sectionnameraw:
                section = str(s['index'])
                bit_comment_start = "Section "+section+". [**"+sectionname.decode('utf-8','ignore').replace('_',' ')+"**]("+base_wikia_url+url_string+") of article "
                url_string = pagenameraw
                url = (base_wikia_url+"api.php?action=parse&page="+pagename.encode('utf-8','ignore')+"&format=xml&prop=images&section="+section)
                sisoup = BeautifulSoup(urllib2.urlopen(url).read())
                try:
                  page_image = sisoup.img.text
                except:
                  page_image = ""
                pic_markdown = "Image from section"

                while url_string.endswith('))'):
                  url_string = url_string.replace('))',')')

                url_string_for_fetch = url_string.replace('_', '%20').replace("\\", "")
                url_string_for_fetch = url_string_for_fetch.replace(' ', '%20').replace("\\", "")
                article_name = url_string.replace('_', ' ')
                article_name_terminal = article_name.decode('utf-8','ignore')
                ### In case user comments like "/wiki/Article.", remove last 1 letter
                if url_string_for_fetch.endswith(".") or url_string_for_fetch.endswith("]"):
                  url_string_for_fetch = url_string_for_fetch[0:--(url_string_for_fetch.__len__()-1)]
                is_section = True
                break
          except Exception as e:
            #traceback.print_exc()
            fail(e)
            continue

          if article_name_terminal == None and not summary_call:
            log("MALFORMATTED LINK")
            #notify = '*Hey '+post.author.name+', that Wikia link is probably malformatted.*\n\n---\n\n'
            #post_reply(notify,post)
            continue
          log("ARTICLE: %s / SECTION #%s @ %s"%(filter(lambda x: x in string.printable, article_name_terminal),section,post.id))
        else:
          section = 0
          pic_markdown = "Image"
          while url_string.endswith('))'):
            url_string = url_string.replace('))',')')

          url_string_for_fetch = url_string.replace('_', '%20').replace("\\", "")
          url_string_for_fetch = url_string_for_fetch.replace(' ', '%20').replace("\\", "")
          article_name = url_string.replace('_', ' ')
          while url_string_for_fetch.endswith('))'):
            url_string_for_fetch = url_string_for_fetch.replace('))',')')


          ### In case user comments like "/wiki/Article.", remove last 1 letter
          if url_string_for_fetch.endswith(".") or url_string_for_fetch.endswith("]"):
            url_string_for_fetch = url_string_for_fetch[0:--(url_string_for_fetch.__len__()-1)]
          url = (base_wikia_url+"api.php?action=query&titles="+url_string_for_fetch+"&prop=pageprops&format=xml")
          try:
            socket.setdefaulttimeout(30)
            pagepropsdata = urllib2.urlopen(url).read()
            pagepropsdata = pagepropsdata.decode('utf-8','ignore')
            ppsoup = BeautifulSoup(pagepropsdata)
            article_name_terminal = ppsoup.page['title']
          except:
            try:
              article_name_terminal = article_name.replace('\\', '')
            except:
              article_name_terminal = article_name.replace('\\', '').decode('utf-8','ignore')

          article_name_terminal = urllib.unquote(article_name_terminal)
          while article_name_terminal.endswith('))'):
            article_name_terminal = article_name_terminal.replace('))',')')
          log("ARTICLE: %s @ %s"%(filter(lambda x: x in string.printable, article_name_terminal),post.id))

          try:
            page_image = ppsoup.pageprops["page_image"]
          except:
            page_image = ""

          if article_name_terminal == None and not summary_call:
            log("MALFORMATTED LINK")
            #notify = '*Hey '+post.author.name+', that Wikia link is probably malformatted.*'
            #post_reply(notify,post)
            continue

        ### Try to find a background/description section
        # Only if the poster did not specify a specific section
        if not section:
          url = (base_wikia_url+"api.php?action=parse&page="+url_string_for_fetch+"&format=xml&prop=sections")
          socket.setdefaulttimeout(30)
          slsoup = BeautifulSoup(urllib2.urlopen(url).read())
          for s in slsoup.find_all('s'):
            if s['line'].lower() in ("description", "background", "about", "biography", "personality", "plot", "characteristics", "history"):
                section = s['index']
                break
        ### fetch data from wikia
        url = (base_wikia_url+"api.php?action=parse&page="+url_string_for_fetch+"&format=xml&prop=text&section="+str(section)+"&redirects")
        try:
          socket.setdefaulttimeout(30)
          sectiondata = urllib2.urlopen(url).read()
          sectiondata = sectiondata.decode('utf-8','ignore')
          sectiondata = reddify(sectiondata)
          soup = BeautifulSoup(sectiondata)
          soup = BeautifulSoup(soup.text)
          sectionnsoup = soup
        except Exception as e:
          fail("FETCH: %s"%e)
          fail("URL: %s"%url)
          continue

        soup = clean_soup(soup)

        ### extract paragraph
        try:
          if soup.p.text.__len__() < 500:
            all_p = soup.find_all('p')
            wt = ""
            for idx, val in enumerate(all_p):
              s = all_p[idx]
              for tag in s:
                if tag.name == 'a' and tag.has_attr('href'):
                  urlstart = ""
                  if re.search('#cite',tag['href']):
                    tag.replace_with('')
                    continue
                  elif re.search('/wikia/',tag['href']):
                    urlstart = "https://"+sub_wikia+".wikia.com"
                  elif re.search('#',tag['href']):
                    tag.unwrap()
                    continue
                  elif not re.search(r'^http://',tag['href']):
                    tag.replace_with(tag.text)
                    continue
                  rep = "["+tag.text+"]("+urlstart+tag['href'].replace(')','\)')+")"
                  discard = tag.replace_with(rep)
              wt = (wt+"\n\n>"+s.text)                                      # Post 3 paragraphs
              data = wt
              if has_list:
                para = 100
              else:
                para = 1
              if idx > para:
                break
          else:
            s = soup.p
            for tag in s:
              if tag.name == 'a' and tag.has_attr('href'):
                urlstart = ""
                if re.search('#cite',tag['href']):
                  tag.replace_with('')
                  continue
                elif re.search('/wiki/',tag['href']):
                  urlstart = "https://"+sub_wikia+".wikia.com"
                elif re.search('#',tag['href']):
                  tag.unwrap()
                  continue
                elif not re.search(r'^http://',tag['href']):
                  tag.replace_with(tag.text)
                  continue
                rep = "["+tag.text+"]("+urlstart+tag['href'].replace(')','\)')+")"
                discard = tag.replace_with(rep)
            data = s.text                             #Post only first paragraph
        except Exception as e:
          fail("TEXT PACKAGE FAIL: %s"%e)
          if summary_call:
            try:
              term = url_string
              tell_me_text = wikia.summary(sub_wikia, term,redirect=True)
              tell_me_link = wikia.page(sub_wikia, term,).url
              title = wikia.page(sub_wikia, term,).title
              if bool(re.search(title,tell_me_text)):
                summary = re.sub(title,"[**"+title+"**]("+tell_me_link+")",tell_me_text)
              else:
                summary = "[**"+title+"**](" + tell_me_link + "): " + tell_me_text
              log("INTERPRETATION: %s"%filter(lambda x: x in string.printable, title))
              if re.search(r'#',title):
                summary = wikia.page(sub_wikia, title.split('#')[0]).section(title.split('#')[1])
                if summary == None or str(filter(lambda x: x in string.printable, summary)).strip() == "":
                  page_url = wikia.page(sub_wikia, title.split('#')[0]).url
                  summary = "Sorry, I failed to fetch the section, but here's the link: "+page_url+"#"+title.split('#')[1]
              if re.search(r'(',page_url):
                page_url = process_brackets_links(page_url)
              comment = "*Here you go:*\n\n---\n\n>\n"+summary+"\n\n---\n\n"
              post_reply(comment,post)
              continue
            except Exception as e:
              if bool(re.search('.*may refer to:.*',filter(lambda x: x in string.printable, str(e)))):
                deflist = ">Definitions for few of those terms:"
                for idx, val in enumerate(filter(lambda x: x in string.printable, str(e)).split('may refer to: \n')[1].split('\n')):
                  deflist = deflist + "\n\n>1. **"+val.strip()+"**: "+ wikia.summary(sub_wikia, val,sentences=1)
                  if idx > 3:
                    break
                #comment = "*Oops,* ***"+process_brackets_syntax(url_string).strip()+"*** *landed me on a disambiguation page.*\n\n---"+deflist+"\n\n---\n\nAnd the remaining list:\n\n"+str(e).replace('\n','\n\n>')+"\n\n---\n\n"
                summary = "*Oops,* ***"+process_brackets_syntax(url_string).strip()+"*** *landed me on a disambiguation page.*\n\n---\n\n"+deflist+"\n\n---\n\n"
                log("ASKING FOR DISAMBIGUATION")
              else:
                log("INTERPRETATION FAIL: %s"%term)
                try:
                  terms = "\""+term+"\""
                  suggest = wikia.search(sub_wikia, terms,results=1)[0]
                  trialsummary = wikia.summary(sub_wikia, suggest,)
                  comment = "*Nearest match for* ***"+term.trim()+"*** *is* ***"+suggest+"*** :\n\n---\n\n>"+trialsummary+"\n\n---\n\n"
                  log("SUGGESTING %s"%suggest)
                except:
                  comment = "*Sorry, couldn't find a wikia article about that or maybe I couldn't process that due to Wikia server errors.*\n\n---\n\n"
                  log("COULD NOT SUGGEST FOR %s"%term)
                post_reply(comment,post)
                continue
          continue
        data = strip_wiki(data)
        data = re.sub("Cite error: There are ref tags on this page, but the references will not show without a \{\{reflist\}\} template \(see the help page\)\.", '', data)
        #truncateddata = truncate(data,1000)
        if data.__len__() < 50:
          log("TOO SMALL INTRODUCTION PARAGRAPH")
          continue
        success("TEXT PACKAGED")

        ### Fetch page image from wikia
        try:
          ### Extract image url
          try:
            page_image = urllib.unquote(page_image.decode('utf-8','ignore'))
          except:
            raise Exception("no page image")
          if page_image.endswith("ogg") or page_image == "":
            raise Exception("no image")
          url = (base_wikia_url+"api.php?action=query&titles=File:"+page_image+"&prop=imageinfo&iiprop=url|mediatype&iiurlwidth=640&format=xml")
          socket.setdefaulttimeout(30)
          wi_api_data = urllib2.urlopen(url).read()
          wisoup = BeautifulSoup(wi_api_data)
          image_url = wisoup.ii['thumburl']
          image_source_url = wisoup.ii['descriptionurl']
          image_source_url = re.sub(r'\)','\)',image_source_url)
          image_source_url = re.sub(r'\(','\(',image_source_url)
          global image_source_markdown
          image_source_markdown = ("[^(i)]("+image_source_url+")")

          ### Upload to imgur
          uploaded_image = im.upload_image(url=image_url, title=page_image)

          ### Extract caption from already fetched sectiondata
          try:
            caption_div = sectionnsoup.find("div", { "class" : "thumbcaption" })
            if caption_div is None:
              raise Exception("caption not packaged: no caption found in section 0")
            if page_image not in str(caption_div.find("div", { "class" : "magnify" })):
              raise Exception("caption not packaged: page image not in section 0")
            discard = caption_div.find("div", { "class" : "magnify" }).extract()
            caption = caption_div.text.strip()
            caption = strip_wiki(caption)
            caption = re.sub(r'\)','\)',caption)
            caption = re.sub(r'\(','\(',caption)
            caption = re.sub(r'\*','',caption)
            caption = re.sub(r'\n',' ',caption)
            if caption != "":
              caption_markdown = (" - *"+caption+"*")
              caption_div = None
              success("CAPTION PACKAGED")
            else:
              raise Exception("caption not packaged: no caption found in section 0")
          except Exception as e:
            if str(e) == "caption not packaged: page image has no caption":
              pic_markdown = "Image"
            elif str(e) == "caption not packaged: page image not in section 0":
              pic_markdown = "Image from article"
            caption_markdown = ""
            log(e)
          image_markdown = ("====\n\n>[**"+pic_markdown+"**]("+uploaded_image.link.replace('http://','https://')+") "+image_source_markdown+caption_markdown)
          success("IMAGE PACKAGED VIA %s"%uploaded_image.link)
        except Exception as e:
          image_markdown = ""
          #traceback.print_exc()
          log("IMAGE: %s"%str(e).strip().replace('\n',''))

        ###Interesting articles
        try:
          intlist = wikia.search(sub_wikia, article_name_terminal,results=5)
          if intlist.__len__() > 1:
            if article_name_terminal in intlist:
              intlist.remove(article_name_terminal)
            interesting_list = ""
            for topic in intlist:
              try:
                topicurl = wikia.page(sub_wikia, topic,).url.replace('(','\(').replace(')','\)')
              except:
                continue
              topic = topic.replace(' ',' ^').replace(' ^(',' ^\(')
              interesting_list = interesting_list + " [^" + topic + "]" + "(" +topicurl.replace('http://','https://')+ ") ^|"
            interesting_markdown = "^Interesting:"+interesting_list.strip('^|')
            success("%s INTERESTING ARTICLE LINKS PACKAGED"%intlist.__len__())
          else:
            raise Exception("no suggestions")
        except Exception as e:
          interesting_markdown = ""
          #traceback.print_exc()
          log("INTERESTING ARTICLE LINKS NOT PACKAGED: %s"%str(e).strip().replace('\n',''))

        ###NSFW tagging
        #badwords = getnsfw(data)
        badwords = None #mark all articles as sfw for now
        if badwords:
          badlist = ''
          for word in badwords:
            badlist = badlist + word + ',%20'
          nsfwurl = "http://www.np.reddit.com/message/compose?to=%28This%20is%20a%20placeholder%29/r/autowikiabot&subject="+str(len(badwords))+"%20NSFW%20words%20are%20present%20in%20this%20comment:&message="+badlist.strip(',%20')+"%0a%0aIf%20you%20think%20any%20of%20word/s%20above%20is%20SFW,%20forward%20this%20message%20to%20/r/autowikiabot%20%28keep%20the%20subject%20unchanged%29%0a%0acontext:"+str(post.permalink)
          nsfwtag = " [](#nsfw-start)**^NSFW** [^^(?)]("+nsfwurl+")[](#nsfw-end)"
          success("FOUND %s NSFW WORDS"%str(len(badwords)))
        else:
          nsfwtag = " [](#sfw)"

        post_markdown = bit_comment_start+" [**"+article_name_terminal+"**](https://"+sub_wikia+".wikia.com/wiki/"+url_string_for_fetch.replace(')','\)')+"):"+nsfwtag+" \n\n---\n\n>"+data+"\n\n>"+image_markdown+"\n\n---\n\n"+interesting_markdown+"\n\n"
        a = post_reply(post_markdown,post)
        image_markdown = ""
        if not a:
          continue

  except KeyboardInterrupt:
    save_changing_variables('exit dump')
    warn("EXITING")
    break
  except Exception as e:
    traceback.print_exc()
    warn("GLOBAL: %s"%e)
    time.sleep(3)
    continue


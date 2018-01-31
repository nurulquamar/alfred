import os
import time
import re
from slackclient import SlackClient
import csv
from urllib.request import urlopen
import codecs
import requests
import json

# instantiate Slack client
slack_client = SlackClient("") //Add the token here
# alfred's user ID in Slack: value is assigned after the bot starts up
alfred_id = None

# constants
RTM_READ_DELAY = 1 # 1 second delay between reading from RTM
CMD_BUGCOUNT = "bugcount"
CMD_BUGCHART = "bugchart"
CMD_HELP = "help"
CMD_INTRO = "introduce"
CMD_LINKS = "buglink"
HELP_TXT = ("Sample Commands:\n"
    "1. bugcount for android ReferAndEarn\n"
    "2. share the bugcount for ios ReferAndEarn\n"
    "3. bugchart for ios ReferAndEarn\n"
    "4. can you give me the bugchart for android ReferAndEarn\n"
    "5. buglink for android ReferAndEarn\n"
    "6. Can you share the buglink for ReferAndEarn sprint of ios?\n"
    )

INTRO_TXT = ("Hello Everyone! I am Alfred. I can help you with bug related queries from Bugzilla.\n"
    "As of now I can do following things:\n"
    "1. Give you link to the bugchart for any sprint.\n"
    "2. Give you link to the buglinks for open/resolved and total bugs for any sprint.\n"
    "3. Give you bug tally for any sprint\n"
    "You can type \"help\" at anytime to get a list of sample commands\n"
    )

MENTION_REGEX = "^<@(|[WU].+)>(.*)"
versions = []
url = 'http://bug.yatra.com/rest/product?names=B2C%20Mobile%20App'
r = requests.get(url)
version_count = r.json()['products'][0]['versions']
curr_item = {}
for v in version_count:
    curr_item = v
    versions.append(curr_item['name'])

def getSprintName(command):
    found = ""
    for sprint in versions:
        if sprint.lower() in command.lower():
            found = sprint
            break
    return found

def getOS(command):
    os = ""
    if "android" in command.lower():
        os = "Android"
    elif "ios" in command.lower():
        os = "iOS"
    elif "backend" in command.lower():
        os = "Mobile_BackEnd"
    return os

def getBugLinks(command,mobileOs,sprintName):
    # mobileOs = getOS(command)
    # sprintName = getSprintName(command)
    found_open = found_resolved = found_total = 0
    # if sprintName=="":
    #     return "Failed to find the version name.\nType help for list of sample commands"
    status_open = "bug_status=Enhancement&bug_status=New&bug_status=ASSIGNED&bug_status=REOPENED"
    status_resolved = "bug_status=RESOLVED"
    status_total = "bug_status=APPROVED&bug_status=DEFERRED&bug_status=Enhancement&bug_status=New&bug_status=UNCONFIRMED&bug_status=CONFIRMED&bug_status=ASSIGNED&bug_status=RESOLVED&bug_status=REOPENED&bug_status=VERIFIED&bug_status=COMPLETED"

    url_open = ("http://bug.yatra.com/buglist.cgi?"+status_open+
        "&op_sys="+mobileOs+"&product=B2C%20Mobile%20App&query_format=advanced&version="+sprintName)
    txt_open = urlopen(url_open)
    for line in txt_open:
        if("bugs found" in str(line)):
            found_open = re.findall("\d+",str(line))[0]
            break
    openBugLink = "Here is the link for Open Bugs for "+mobileOs+" "+sprintName+":\n"+url_open+"\n(Count[Enhancement+New+Assigned+Reopened]: "+str(found_open)+")"

    url_resolved = ("http://bug.yatra.com/buglist.cgi?"+status_resolved+
        "&op_sys="+mobileOs+"&product=B2C%20Mobile%20App&query_format=advanced&version="+sprintName)
    txt_resolved = urlopen(url_resolved)
    for line in txt_resolved:
        if("bugs found" in str(line)):
            found_resolved = re.findall("\d+",str(line))[0]
            break
    resolvedBugLink = "Here is the link for Resolved Bugs for "+mobileOs+" "+sprintName+":\n"+url_resolved+"\n(Count[Resolved]: "+str(found_resolved)+")"

    url_total = ("http://bug.yatra.com/buglist.cgi?"+status_total+
        "&op_sys="+mobileOs+"&product=B2C%20Mobile%20App&query_format=advanced&version="+sprintName)
    txt_total = urlopen(url_total)
    for line in txt_total:
        if("bugs found" in str(line)):
            found_total = re.findall("\d+",str(line))[0]
            break
    totalBugLink = "Here is the link for Total Bugs for "+mobileOs+" "+sprintName+":\n"+url_total+"\n(Count[Total]: "+str(found_total)+")"

    return openBugLink+"\n\n"+resolvedBugLink+"\n\n"+totalBugLink

def getBugChart(command,mobileOs,sprintName):
    # mobileOs = getOS(command)
    # sprintName = getSprintName(command)
    # if sprintName=="":
    #     return "Failed to find the version name.\nType help for list of sample commands"
    url = ("http://bug.yatra.com/report.cgi?bug_severity=blocker&bug_severity=critical&bug_severity=major&bug_severity=normal&"
    "bug_severity=minor&bug_severity=trivial&bug_severity=enhancement&bug_status=APPROVED&bug_status=DEFERRED&"
    "bug_status=Enhancement&bug_status=New&bug_status=UNCONFIRMED&bug_status=CONFIRMED&bug_status=ASSIGNED&"
    "bug_status=RESOLVED&bug_status=REOPENED&bug_status=VERIFIED&bug_status=COMPLETED&"
    "op_sys="+mobileOs+""
    "&product=B2C%20Mobile%20App&version="+sprintName+""
    "&x_axis_field=bug_severity&y_axis_field=bug_status&width=1024&height=600&action=wrap&format=table")
    return "You can check the Bug chart here:\n"+url

def getBugCount(command,mobileOs,sprintName):
    # mobileOs = "iOS"
    # if("android" in command.lower()):
    #     mobileOs = "Android"
    # sprintName = getSprintName(command)
    # if sprintName=="":
    #     return "Failed to find the version name.\nType help for list of sample commands"
    count_open = 0
    count_deferred = 0
    count_resolved = 0
    count_closed = 0
    count_total = 0
    url = ("http://bug.yatra.com/report.cgi?bug_severity=blocker&bug_severity=critical&bug_severity=major&bug_severity=normal&"
    "bug_severity=minor&bug_severity=trivial&bug_severity=enhancement&bug_status=APPROVED&bug_status=DEFERRED&"
    "bug_status=Enhancement&bug_status=New&bug_status=UNCONFIRMED&bug_status=CONFIRMED&bug_status=ASSIGNED&"
    "bug_status=RESOLVED&bug_status=REOPENED&bug_status=VERIFIED&bug_status=COMPLETED&"
    "op_sys="+mobileOs+""
    "&product=B2C%20Mobile%20App&version="+sprintName+""
    "&x_axis_field=bug_severity&y_axis_field=bug_status&width=1024&height=600&action=wrap&ctype=csv&format=table")
    ftpstream = urlopen(url)
    csvfile = csv.reader(codecs.iterdecode(ftpstream, 'utf-8'))
    status = []
    severity = []
    rownum = 0
    for row in csvfile:
        if rownum==0:
            for i in range(1,len(row)):
                severity.append(row[i])
        else:
            status.append(row[0])
        rownum+=1

        #Get Open Bug Count
        if(row[0].lower() == "new" or row[0].lower== "reopened" or row[0].lower==""):
            for i in range(1,len(row)):
                count_open += int(row[i])

        #Get Closed Bug Count
        if(row[0].lower() == "verified"):
            for i in range(1,len(row)):
                count_closed += int(row[i])

        #Get Resolved Bug Count
        if(row[0].lower() == "resolved"):
            for i in range(1,len(row)):
                count_resolved += int(row[i])

        #Get Deferred Bug Count
        if(row[0].lower() == "deferred"):
            for i in range(1,len(row)):
                count_deferred += int(row[i])

        #Total Bugs
        count_total = count_deferred+count_open+count_resolved+count_closed

    finalCount = "Here is the Bug Tally for "+mobileOs+" "+sprintName+":\nOpen Bugs: "+str(count_open)+"\nResolved Bugs: "+ str(count_resolved)+"\nClosed Bugs: "+str(count_closed)+"\nDeferred Bugs: "+str(count_deferred)+"\nTotal Bugs: "+str(count_total)
    return finalCount

def parse_bot_commands(slack_events):
    """
        Parses a list of events coming from the Slack RTM API to find bot commands.
        If a bot command is found, this function returns a tuple of command and channel.
        If its not found, then this function returns None, None.
    """
    for event in slack_events:
        if event["type"] == "message" and not "subtype" in event:
            user_id, message = parse_direct_mention(event["text"])
            if user_id == starterbot_id:
                return message, event["channel"]
    return None, None

def parse_direct_mention(message_text):
    """
        Finds a direct mention (a mention that is at the beginning) in message text
        and returns the user ID which was mentioned. If there is no direct mention, returns None
    """
    matches = re.search(MENTION_REGEX, message_text)
    # the first group contains the username, the second group contains the remaining message
    return (matches.group(1), matches.group(2).strip()) if matches else (None, None)

def handle_command(command, channel):
    """
        Executes bot command if the command is known
    """
    # Default response is help text for the user
    response = default_response = "Not sure what you mean. Try *{} Android ReferAndEarn * .".format(CMD_BUGCOUNT)

    if (CMD_BUGCOUNT in command) or (CMD_BUGCHART in command) or (CMD_LINKS in command):
        mobileOs = getOS(command)
        sprintName = getSprintName(command)

        if sprintName=="":
            response = "Sorry! I couldn't understand the Sprint Name.\nType \"help\" for list of sample commands"
        elif mobileOs=="":
            response = "Sorry! I couldn't understand the OS name.\nType \"help\" for list of sample commands"

        elif CMD_BUGCOUNT in command:
            response = getBugCount(command,mobileOs,sprintName)

        elif CMD_BUGCHART in command:
            response = getBugChart(command,mobileOs,sprintName)

        elif CMD_LINKS in command:
            response = getBugLinks(command,mobileOs,sprintName)

    elif CMD_HELP in command:
        response = HELP_TXT

    elif CMD_INTRO in command:
        response = INTRO_TXT

    elif ("thanks" in command.lower()) or ("thank you" in command.lower()):
        response = "Welcome! By the way you can also Thank me by treating Mobile QA Team with Pizza ;) "

    # Sends the response back to the channel
    slack_client.api_call("chat.postMessage",channel=channel, text=response or default_response)

    # Sending another message
    if(CMD_INTRO in command):
        wip = "Please note... I am still a work in progress. Mobile QA team is working on enhancements and new features. You can send your suggestions and feedbacks to Mobile QA."
        slack_client.api_call("chat.postMessage", channel=channel, text=wip)

if __name__ == "__main__":
    if slack_client.rtm_connect(with_team_state=False):
        print("Starter Bot connected and running!")
        # Read bot's user ID by calling Web API method `auth.test`
        starterbot_id = slack_client.api_call("auth.test")["user_id"]
        while True:
            command, channel = parse_bot_commands(slack_client.rtm_read())
            if command:
                handle_command(command, channel)
            time.sleep(RTM_READ_DELAY)
    else:
        print("Connection failed. Exception traceback printed above.")

#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import requests
import sys
import re
import concurrent.futures
import functools

SONARCLOUD_HOST = "https://sonarcloud.io"
PAGE_SIZE = 500
MAX_WORKERS=10

ORANGE='\033[0;35m'
GREEN='\033[92m'
BLUE='\033[94m'
YELLOW='\033[33m'
BOLD='\033[1m'
NOCOLOR='\033[0m'

def main():
    parser = argparse.ArgumentParser(description=BOLD+'Sonarleaks 🛰️💧'+NOCOLOR+" Search for private code published to Sonarcloud.")
    parser.add_argument('--top', action="store_true", default=False, required=False, dest='top', help = "Filter on top public projects")
    parser.add_argument('--loc', type=int, required=False, default=0, dest='loc', help = "Filter on minimum of lines of code")
    parser.add_argument('-k', type=str, required=False, dest='keyword', help = "Keyword (company, project, etc.)")
    parser.add_argument('-kf', type=str, required=False, dest='keyword_file', help = "Keywords file")
    parser.add_argument('--private', action="store_true", default=False, required=False, dest='private', help = "Only display components linked to potential private repository.")
    parser.add_argument('--source', action="store_true", default=False, required=False, dest='source', help = "Only display components with available source code.")
    args = parser.parse_args()
    private = args.private
    source = args.source
    loc = args.loc

    keywords = []
    if args.top:
        process_keyword("", private, source, loc)
    else:
        if args.keyword:
            keywords.append(args.keyword)
        if args.keyword_file:
            with open(args.keyword_file, 'r') as f:
                keywords.extend([line.strip() for line in f.readlines()])
    
        for keyword in keywords:
            print(BLUE+"\n[*] Searching for projects related to keyword "+keyword+NOCOLOR)
            process_keyword(keyword, private, source, loc)

    print(BLUE+"\n[*] Happy (ethical) hacking!"+NOCOLOR)

def process_keyword(keyword: str, private: bool, source: bool, loc: int):
    # Search only by keyword
    components = search_projects(keyword, loc=loc)
    
    # Search by organization (exact term)
    if (keyword != ""):
        organizations = search_organizations(keyword)
        for organization in organizations:
            organization_name = organization['name']
            organization_key = organization['key']
            print(GREEN+"[+] Found organization with key '"+organization_key+"' and name '"+organization_name+"' (exact term only). Check this: https://sonarcloud.io/organizations/"+organization_key+NOCOLOR)
            print(BLUE+"[*] Searching for projects related to organization '"+organization_name+"'"+NOCOLOR)
            components_organisation = search_projects_for_organization(organization_key)
            if (components_organisation is not None):
                components = components + components_organisation

    print(f"{BLUE}[*] Processing the results ({len(components)} items) ...{NOCOLOR}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        process_result_configured_function = functools.partial(process_results, keyword=keyword, private=private, source=source)
        executor.map(process_result_configured_function, components)
    
def process_results(component: any, keyword: str, private: bool, source: bool):
    component_name = component['name']
    component_key = component['key']
    organization_key = component['organization']
    source_available = check_project_code_available(component_key)
    repository = check_repository(component_key)
    vulnerabilities_count = check_vulnerabilities(component_key)
    if ((repository is not None and repository.url is not None and repository.is_private == True and private == True) or private == False) and ((source == True and source_available == True) or source == False):
        if (keyword == "" or organization_key == keyword or filter_project_key(keyword, component_key)):
            print(GREEN+"\n[+] Found component with key '"+component_key+"' and name '"+component_name+"' from organisation "+"'"+organization_key+"'. Check this: https://sonarcloud.io/project/overview?id="+component_key+NOCOLOR)
            
            if (source_available):
                print(YELLOW+"[+] Found source code available on https://sonarcloud.io/code?id=" + component_key + " !" + NOCOLOR)
            
            if (vulnerabilities_count is not None and int(vulnerabilities_count) > 0):
                print(ORANGE+"[!] This component '" + component_key + "' has " + vulnerabilities_count + " vulnerabilities !" + NOCOLOR) 
            
            if (repository is not None):
                print(GREEN+"[+] This component resides in: " + repository.url + NOCOLOR)
                if (repository.is_private == True):
                    print(ORANGE+"[!] This repository seems to be private! Check this: " + repository.url + NOCOLOR)


def search_organizations(keyword: str):
    print(f"{BLUE}[*] Looking for organizations (exact term){NOCOLOR}")
    ORGS_SEARCH_ENDPOINT=f"{SONARCLOUD_HOST}/api/organizations/search?organizations={keyword}"

    session = requests.Session()
    response = session.get(ORGS_SEARCH_ENDPOINT)
    if (response.status_code != 200):
        fail("Cannot search for organizations.")
    else:
        organizations = response.json()["organizations"]
        return organizations

def search_projects_for_organization(organization: str,page: int = 1):
    print(f"{BLUE}[*] Looking for projects from organization {organization} (page {page}) {NOCOLOR}")
    PROJECTS_ORGS_SEARCH_ENDPOINT=f"{SONARCLOUD_HOST}/api/components/search_projects?ps={PAGE_SIZE}&organization={organization}&p={page}"

    session = requests.Session()
    response = session.get(PROJECTS_ORGS_SEARCH_ENDPOINT)
    if (response.status_code != 200):
        fail("Cannot search for organization projects.")
    else:
        total = int(response.json()["paging"]["total"])
        components = response.json()["components"]
        if (components is not None and total > PAGE_SIZE and (page * PAGE_SIZE) < total):
            components = components + search_projects_for_organization(organization, page+1)
        return components

def search_projects(keyword: str,page: int = 1,loc: int = 0):
    if (keyword != ""):
        print(f"{BLUE}[*] Looking for projects from keyword {keyword} (page {page}){NOCOLOR}")
        PROJECTS_SEARCH_ENDPOINT=f"{SONARCLOUD_HOST}/api/components/search_projects?ps={PAGE_SIZE}&filter=query+%3D+%22{keyword}%22%20and%20ncloc%20%3e%3d%20{loc}&p={page}"
    else:
        print(f"{BLUE}[*] Looking for top projects (page {page}){NOCOLOR}")
        PROJECTS_SEARCH_ENDPOINT=f"{SONARCLOUD_HOST}/api/components/search_projects?ps={PAGE_SIZE}&filter=ncloc%20%3e%3d%20{loc}&p={page}"

    session = requests.Session()
    response = session.get(PROJECTS_SEARCH_ENDPOINT)
    if (response.status_code != 200):
        fail("Cannot search for projects.")
    else:
        total = int(response.json()["paging"]["total"])
        components = response.json()["components"]
        if (components is not None and total > PAGE_SIZE and (page * PAGE_SIZE) < total):
            components = components + search_projects(keyword, page+1, loc)
        return components

def check_project_code_available(project_key: str):
    PROJECTS_BRANCHES_ENDPOINT=f"{SONARCLOUD_HOST}/api/project_branches/list?project={project_key}"

    session = requests.Session()
    response = session.get(PROJECTS_BRANCHES_ENDPOINT)
    if (response.status_code != 200):
        fail(f"\nCannot search for project code with key {project_key}.")
    else:
        branches = response.json()["branches"]
        if (len(branches) > 0 and "commit" in branches[0]):
            return True

def filter_project_key(keyword: str, project_key: str):
    # Ex: "_THEPROJECT1", "THEPROJECT-" ...
    special_characters = "_-:/1234567890"

    pattern = rf"(.)?{keyword}(.)?"
    match = re.search(pattern, project_key, re.IGNORECASE)

    if match:

        before_char = match.group(1) if match.group(1) else ""
        after_char = match.group(2) if match.group(2) else ""
        
        if (before_char == "" and special_characters.find(after_char) != -1):
            return True
        elif (after_char == "" and special_characters.find(before_char) != -1):
            return True
        # project_key contains the keyword which begins and ends with special char
        elif (special_characters.find(after_char) != -1 and special_characters.find(before_char) != -1):
            return True
        # project_key contains the keyword in upper case
        elif (project_key.find(keyword.upper()) != -1):
            return True
        else:
            return False
    else:
        return None

def check_vulnerabilities(component_key: str):
    COMPONENT_VULNERABILITIES_ENDPOINT=f"{SONARCLOUD_HOST}/api/measures/component?metricKeys=vulnerabilities&component={component_key}"
    
    session = requests.Session()
    response = session.get(COMPONENT_VULNERABILITIES_ENDPOINT)
    if (response.status_code != 200):
        fail(f"\nCannot get measures from component {component_key}.")
    else:
        component = response.json()["component"]
        if ("measures" in component and len(component["measures"]) > 0):
            return component["measures"][0]["value"]

class Repository:
    def __init__(self, url, is_private):
        self.url = url
        self.is_private = is_private

def check_repository(component_key: str):
    COMPONENT_INFO_ENDPOINT=f"{SONARCLOUD_HOST}/api/navigation/component?component={component_key}"

    session = requests.Session()
    response = session.get(COMPONENT_INFO_ENDPOINT)
    if (response.status_code != 200):
        fail("Cannot get measures from component.")
    else:
        response_json = response.json()
        if ("alm" in response_json and "url" in response_json["alm"]):
            url = response_json["alm"]["url"]
            session_test_repository = requests.Session()
            response = session_test_repository.get(url)
            if (response.status_code != 200 and response.status_code != 404):
                return Repository(url,True)
            else:
                return Repository(url,False)

def fail(msg, exit=False):
    print(ORANGE+"[-] Error: "+msg+NOCOLOR)
    if exit:
        sys.exit()

if __name__ == '__main__':
    main()

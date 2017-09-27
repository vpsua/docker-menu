#!/usr/bin/python

import time
import re
import os
import tarfile
import json
from urllib2 import urlopen
from urllib import urlretrieve
from urlparse import urljoin
from subprocess import Popen, PIPE
import yaml
from jinja2 import Environment
from dialog import Dialog


class DockerDialog(object):
    """
    Class, which uses dialog for rendering menu, jinja tempaltes and yaml config for starting docker containers
    URL with our docker repo and config should be provided during class init with base_url
    As a result you will recieve running docker container. It doesn't return anything
    """
    def __init__(self, base_url):
        self.dialog = Dialog()
        self.dialog.set_background_title("Docker composing")
        self.base_url = base_url
        self.template = ""
        self.category = ""
        self.template_directory = ""
        self.base_directory = os.path.expanduser("~")
        self.stage = 0
        self.vars = {}
        self.binaries = ["docker", "docker-compose", "dialog"]
        self.check_requirments()
        try:
            if self.dialog.yesno(
                "Do you want to create Docker container from the list of preinstalled images?",
                width=50
            ) == self.dialog.DIALOG_OK:
                self.dialog.infobox("Loading list of templates", title="Loading...", height=5)
                self.config = yaml.load(urlopen(urljoin(self.base_url, "docker.yml")))
                # self.category_window()
            else:
                self.dialog_exit(manually=True)
        except KeyboardInterrupt:
            self.dialog_exit(manually=True)

    def check_requirments(self):
        """
        Function, that checks if required bineries exist within $PATH
        """
        for program in self.binaries:
            exists = 0
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, program)
                if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
                    exists = 1
            if exists == 0:
                self.dialog_exit(manually="binary")
        return None

    def dialog_exit(self, manually=False):
        """
        Runned in case of user exit from dialog
        """
        if manually is False:
            self.dialog.infobox(
                """Script ends normally.
It may take several minutes to initialize an application inside the Docker container.

You may run this script anytime with the command:
                docker-dialog""",
                title="Exiting...",
                width=50
                )
            time.sleep(5)
            os.system('clear')
            raise SystemExit(0)

        elif manually is True:
            self.dialog.infobox(
                """Script stops on user request.

You may run this script anytime with the command:
                docker-dialog""",
                title="Exiting...",
                width=50
                )
            time.sleep(5)
            os.system('clear')
            raise SystemExit(0)
        elif manually == "binary":
            self.dialog.infobox(
                """Script stops as it didn't find required binaries.

Please, check that listed binaries are installed within $PATH:
        {0}""".format(self.binaries),
                title="Required binaries not found...",
                width=50
                )
            time.sleep(5)
            os.system('clear')
            raise SystemExit(0)
        else:
            # TODO: This part of the script will never happen...
            self.dialog.infobox(
                """Script exits abnormally.

Please, contact support or try run script one more time with the command:
                docker-dialog""",
                title="Exiting...",
                width=50
                )
            time.sleep(5)
            os.system('clear')
            raise SystemExit(1)

    def dialog_help(self, url='README'):
        """
        Runned in case of asking for a help. It should be read from README file
        """
        help_msg = urlopen(urljoin(self.base_url, url)).read()
        self.dialog.msgbox(
            help_msg,
            width=100,
            title="Help")

    def get_url(self, url):
        """
        Downloads files, which are set in the url section.
        If it's j2 template - parse it and save as .yml in template_directory
        """
        # getting filename without jinja extension
        match_jinja = re.match(r"^.*\/(.*)\.j2$", url, re.IGNORECASE)

        try:
            # downloading template
            file_from_url = urlopen(urljoin(self.base_url, url)).read()
            if match_jinja:
                # if it's jinja template - replacing variables with dict
                # dict should be generated with self.get_variable()
                final_data = Environment(autoescape=True).from_string(file_from_url).render(self.vars)
                filename = match_jinja.group(1)
            else:
                # If it's nont jinja - we just getting filename
                final_data = file_from_url
                filename = re.match(r"^.*\/(.*)", url).group(1)

            # saving file
            file_destination = open(os.path.join(self.template_directory, filename), 'w')
            file_destination.write(final_data)
            file_destination.close()
        except:
            try:
                exit_code = self.dialog.msgbox(
                    "Loading failed. Please try installation again", title="Failed!"
                    )

                if exit_code == self.dialog.OK:
                    self.main_window()
                else:
                    self.dialog_exit(manually=True)
            except KeyboardInterrupt:
                self.dialog_exit(manually=True)
            finally:
                os.unlink(os.path.join(self.template_directory, filename))

    def get_bundle(self, bundle):
        """
        Downloads bundle and extracts it to the template directory
        Bundle should be an archive, packed with bz2 or gzip
        """
        # selecting only filename from URL
        bundle_file = re.match(r"^.*\/(.*)", bundle).group(1)
        bundle_path = os.path.join(self.template_directory, bundle_file)
        try:
            # downloading bundle
            urlretrieve(urljoin(self.base_url, bundle), bundle_path)
            # checking bundle extension
            if (
                bundle_file.endswith("tar.gz") or bundle_file.endswith(".tgz") or
                bundle_file.endswith("tar.bz2") or bundle_file.endswith(".tbz")
            ):
                # unpacking it to the template_directory
                with tarfile.open(bundle_path, 'r:gz') as tar_archive:
                    tar_archive.extractall(path=self.template_directory)
        except:
            try:
                exit_code = self.dialog.msgbox(
                    "Loading failed. Please try installation again",
                    title="Failed!")
                if exit_code == self.dialog.OK:
                    self.category_window()
                else:
                    self.dialog_exit(manually=True)
            except KeyboardInterrupt:
                self.dialog_exit(manually=True)
        finally:
            os.unlink(bundle_path)

    def run_composer(self):
        """
        Runs docker composer and dialog programbox for output
        Returns dialog exit code
        """
        # Running composer
        docker_compose = Popen(
            ["docker-compose", "up", "-d"],
            stdout=PIPE,
            stderr=PIPE,
            cwd=self.template_directory)
        # Rendering stdout in programbox
        code = self.dialog.progressbox(
            fd=docker_compose.stderr.fileno(),
            text="Installation progress")
        return code

    def show_value_error(self, errorid):
        """
        This function is used to show error message when user input is invalid
        """
        errormessage = {2: "Passwords does not match or input was empty. Please, try again",
                        1: "Input was empty. Please, try again"}
        self.dialog.infobox(
            errormessage[errorid],
            title="Error",
            width=50
        )
        time.sleep(2)

    def get_variable(self, param):
        """
        Asks user to fullfill required variables
        """
        try:
            # If it's password field, we render passwordbox and ask for a password twice
            asks = [1]
            if re.match(r".*password.*", param, re.IGNORECASE): asks = [1, 2]
            value = {}
            stopflag = False
            messagetext = {1: "Please, input {0}".format(param),
                           2: "Please, input {0} one more time".format(param)}
            while True:
                if len(asks) > 1:
                    msgbox = "passwordbox"
                else:
                    msgbox = "inputbox"
                for i in asks:
                    # Asking password twice and item once
                    exit_code, value[i] = getattr(self.dialog, msgbox)(
                        text=messagetext[i],
                        insecure=True
                    )
                    if exit_code != self.dialog.OK:
                        if exit_code == self.dialog.CANCEL:
                            stopflag = True
                            break
                        # we don't need to exit loop as function below will
                        # exit script itself
                        self.dialog_exit(manually=True)
                if stopflag: break

                if value[1]:
                    try:
                        if value[1] == value[2]:
                            self.vars.update({param: value[2]})
                            break
                        else:
                            self.show_value_error(len(asks))
                    except KeyError:
                        self.vars.update({param: value[1]})
                        break
                else:
                    self.show_value_error(len(asks))
            if stopflag: return False
            else: return True
        except (KeyboardInterrupt):
            self.dialog_exit(manually=True)

    def get_version(self, app):
        """
        Function, that retrieves available tags for docker application
        Application should be passed as an app argument and should be valid docker image name
        Returns True if selection was successfull, False if some exception occured.
        """
        try:
            self.dialog.infobox("Loading list of available versions", title="Loading...", height=5)
            try:
                # Retrieving available tags from dockerhub
                app_versions = json.load(
                    urlopen(
                        "https://registry.hub.docker.com/v1/repositories/{0}/tags".format(app)
                    )
                )
                # Generating list of tuples, as required for docker treeview widget
                dialog_tree = [
                    (
                        ver['name'],
                        ver['name'],
                        0 if ver['name'] != 'latest' else 1,
                        len(re.split(r'\.|\-', ver['name']))-1
                    )
                    for ver in app_versions
                ]
                # Show user version tree
                exit_code, tag = self.dialog.treeview(
                    "Please, select version from the list below",
                    nodes=dialog_tree
                )
                if exit_code == self.dialog.OK:
                    self.vars.update({app: tag})
                    return True
                else:
                    self.vars.update({app: "latest"})
                    return False

            except:
                self.vars.update({app: "latest"})
                return False
        except KeyboardInterrupt:
            self.dialog_exit(manually=True)
        return True

    def app_window(self):
        """
        This window is used to select category and application
        """
        try:
            # exit_code = ""
            app_tuple = []
            if self.stage == 0:
                title = "Category selection"
                dialogtext = "Please, select the matching category from the list:"
                items = self.config.iteritems()
                # TODO: set descriptionname the same in both functions
                decitemname = 'description'
            elif self.stage == 1:
                title = "Template selection"
                dialogtext = "Please, select the matching template from the list:"
                items = self.config[self.category]['options'].iteritems()
                decitemname = 'desc'
            for key, val in items:
                app_tuple.append((key, val[decitemname], val[decitemname]))
            while True:
                # display menu
                exit_code, appcat = self.dialog.menu(
                    text=dialogtext,
                    choices=app_tuple,
                    title=title,
                    help_button=True,
                    item_help=True
                )
                if exit_code == self.dialog.OK:
                    if self.stage == 0: self.category = appcat
                    elif self.stage == 1: self.template = appcat
                    break
                elif exit_code == self.dialog.HELP:
                    self.dialog_help()
                    continue
                elif exit_code == self.dialog.CANCEL:
                    break
                else:
                    self.dialog_exit(manually=True)
            return exit_code
        except (KeyboardInterrupt):
            self.dialog_exit(manually=True)

    def category_window(self):
        """
        Window with category selection
        """
        try:
            # generating list of the categories from the config
            category_tuple = []
            for key, val in self.config.iteritems():
                category_tuple.append((key, val['description'], val['description']))
            while True:
                # display menu with category selection
                exit_code, self.category = self.dialog.menu(
                    text="Please, select the matching category from the list:",
                    choices=category_tuple,
                    title="Category selection",
                    help_button=True,
                    item_help=True
                )
                if exit_code == self.dialog.OK:
                    break
                elif exit_code == self.dialog.HELP:
                    self.dialog_help()
                    continue
                else:
                    self.dialog_exit(manually=True)
        except (KeyboardInterrupt):
            self.dialog_exit(manually=True)
        return exit_code
        # self.main_window()

    def variables_input(self):
        """
        Function-stage, to collect following information from user:
            - software versions to install
            - some custom variables (ports, passwords, etc)

        Returns "ok" if everything retrieved successfull, "cancel" if not
        """
        # Checking if version can be specified by user     
        if "version" in self.config[self.category]['options'][self.template]:
            # Asking user if he wants to select version
            if self.dialog.yesno(
                    """Do you want to select version of {0}?
Latest version will be installed by default""".format(",".join([app for app in self.config[self.category]['options'][self.template]['version']])),
                    width=50
            ) == self.dialog.DIALOG_OK:
                # As he want, we're iterating over available applications to setup versions
                for application in self.config[self.category]['options'][self.template]['version']:
                    self.get_version(application)
            else:
                # As he doesn't want, we fullfill information with the "latest" version
                self.vars.update({app: "latest" for app in self.config[self.category]['options'][self.template]})
        exit_code = []
        # checking if we have vars, that needs to be fullfield by the user
        if "vars" in self.config[self.category]['options'][self.template]:
            for variable in self.config[self.category]['options'][self.template]['vars']:
                exit_code.append(self.get_variable(variable))
                if exit_code[-1] == False: break
        # TODO: ADD substage for the variables configuration
        if all(exit_code): return "ok"
        else: return "cancel"

    def postinstall(self):
        """
        Perform installation and download necessary files
        """
        # Create Directories
        self.template_directory = os.path.join(self.base_directory, self.template)
        if not os.path.exists(self.template_directory):
            os.makedirs(self.template_directory)

        self.dialog.infobox("Loading composer files", title="Loading...", height=5)
        # checking, if we have urls, that needs to be downloaded
        if "urls" in self.config[self.category]['options'][self.template]:
            for url in self.config[self.category]['options'][self.template]['urls']:
                self.get_url(url)

        # checking, if we have bundle, that needs to be downloaded
        if "bundle" in self.config[self.category]['options'][self.template]:
            self.get_bundle(self.config[self.category]['options'][self.template]['bundle'])

        if "dirs" in self.config[self.category]['options'][self.template]:
            for folder in self.config[self.category]['options'][self.template]['dirs']:
                try:
                    os.makedirs(os.path.join(self.template_directory, folder))
                except OSError:
                    pass

        # running docker composer
        self.run_composer()
        try:
            self.dialog_help(url=self.config[self.category]['options'][self.template]['help'])
        finally:
            self.dialog_exit()
        pass

    def main_window(self):
        """
        Window with template selectionselection
        """
        try:
            # Generating a list of supported templates from the config
            template_tuple = []
            for key, val in self.config[self.category]['options'].iteritems():
                template_tuple.append((key, val['desc'], val['desc']))

            while True:
                # display matched templates from the self.category
                exit_code, self.template = self.dialog.menu(
                    text="Please, select the matching template from the list:",
                    choices=template_tuple,
                    title="Template selection",
                    help_button=True,
                    item_help=True
                    )

                if exit_code == self.dialog.OK:
                    break
                elif exit_code == self.dialog.HELP:
                    self.dialog_help()
                    continue
                elif exit_code == self.dialog.CANCEL:
                    break
                else:
                    self.dialog_exit(manually=True)
            return exit_code

        except (KeyboardInterrupt):
            self.dialog_exit(manually=True)


def main():
    base_url = "http://repo.vps.ua/docker/"
    ydialog = DockerDialog(base_url)
#    if ydialog.category_window() == "ok":
#        ydialog.stage += 1
    # ydialog.main_window()

    while True:
        ret_code = -1
        # Category and app selection stage
        if ydialog.stage == 0 or ydialog.stage == 1:
            ret_code = ydialog.app_window()
        # Variables input stage
        if ydialog.stage == 2: ret_code = ydialog.variables_input()
        # Installation stage (exits script)
        if ydialog.stage == 3: ydialog.postinstall()
        # Perform stage change based on return code
        if ret_code == "ok": ydialog.stage += 1
        else: ydialog.stage -= 1
        # if we are trying to return from the very first stage, we should exit
        if ydialog.stage == -1: ydialog.dialog_exit(manually=True)
if __name__ == "__main__":
    main()

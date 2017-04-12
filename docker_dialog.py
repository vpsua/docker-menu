#!/usr/bin/python

import time
import re
import os
import tarfile
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
        self.vars = {}
        if self.dialog.yesno(
                "Do you want to create Docker container from the list of preinstalled images?",
                width=50
            ) == self.dialog.DIALOG_OK:

            self.dialog.infobox("Loading list of templates", title="Loading...", height=5)
            self.config = yaml.load(urlopen(urljoin(self.base_url, "docker.yml")))
            self.category_window()

        else:
            self.dialog_exit()


    def dialog_exit(self):
        """
        Runned in case of user exit from dialog
        """
        self.dialog.infobox(
            """Script ends normally.

You may run this script anytime with command:
        /opt/scripts/docker_dialog.py""",
            title="Exiting...",
            width=50
            )
        time.sleep(3)
        os.system('clear')
        raise SystemExit(0)


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
            exit_code = self.dialog.msgbox(
                "Loading failed. Please try installation again", title="Failed!"
                )

            if exit_code == self.dialog.OK:
                self.main_window()
            else:
                self.dialog_exit()
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
            exit_code = self.dialog.msgbox(
                "Loading failed. Please try installation again",
                title="Failed!")
            if exit_code == self.dialog.OK:
                self.category_window()
            else:
                self.dialog_exit()
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
        code = self.dialog.programbox(
            fd=docker_compose.stderr.fileno(),
            text="Installation progress")
        return code

    def get_variable(self, param):
        """
        Asks user to fullfill required variables
        """
        # If it's password field, we render passwordbox and ask for a password twice
        if re.match(r".*password.*", param, re.IGNORECASE):
            # Asking password first time
            exit_code, password1 = self.dialog.passwordbox(
                text="Please, input {0}".format(param),
                insecure=True
                )
            if exit_code == self.dialog.OK:
                # Asking password second time
                exit_code, password2 = self.dialog.passwordbox(
                    text="Please, input {0} one more time".format(param),
                    insecure=True
                    )
                if exit_code == self.dialog.OK:
                    # comparing input. If input equal - updating dict. In other case - ask again
                    if (password1 == password2) and password1:
                        self.vars.update({param: password2})
                    else:
                        self.dialog.infobox(
                            "Passwords does not match or input was empty. Please, try again",
                            title="Error",
                            width=50
                            )
                        time.sleep(2)
                        self.get_variable(param)
                elif exit_code == self.dialog.CANCEL:
                    self.get_variable(param)
                else:
                    self.dialog_exit()
            elif exit_code == self.dialog.CANCEL:
                self.main_window()
            else:
                self.dialog_exit()

        else:
            # If variable is not passsword, asking for a value in inputbox without check
            exit_code, value = self.dialog.inputbox(
                text="Please, input {0}".format(param),
                insecure=True
                )
            if exit_code == self.dialog.OK:
                if value:
                    self.vars.update({param: value})
                else:
                    self.dialog.infobox(
                        "Input was empty. Please, try again",
                        title="Error",
                        width=50
                        )
                    time.sleep(2)
                    self.get_variable(param)
            elif exit_code == self.dialog.CANCEL:
                self.main_window()
            else:
                self.dialog_exit()

    def category_window(self):
        """
        Window with category selection
        """
        # generating list of the categories from the config
        category_tuple = []
        for key, val in self.config.iteritems():
            category_tuple.append((key, val['description'], val['description']))

        # display menu with category selection
        exit_code, self.category = self.dialog.menu(
            text="Please, select the matching category from the list:",
            choices=category_tuple,
            title="Category selection",
            help_button=True,
            item_help=True
            )

        if exit_code == self.dialog.OK:
            self.main_window()

        elif exit_code == self.dialog.HELP:
            self.dialog_help()
            self.category_window()

        else:
            self.dialog_exit()

    def main_window(self):
        """
        Window with template selectionselection
        """
        # Generating list of supported templates from the config
        template_tuple = []
        for key, val in self.config[self.category]['options'].iteritems():
            template_tuple.append((key, val['desc'], val['desc']))

        # display matched templates from the self.category
        exit_code, self.template = self.dialog.menu(
            text="Please, select the matching template from the list:",
            choices=template_tuple,
            title="Template selection",
            help_button=True,
            item_help=True
            )

        if exit_code == self.dialog.OK:

            self.template_directory = os.path.join(self.base_directory, self.template)

            if not os.path.exists(self.template_directory):
                os.makedirs(self.template_directory)

            # checking if we have vars, that needs to be fullfield by the user
            if "vars" in self.config[self.category]['options'][self.template]:
                for variable in self.config[self.category]['options'][self.template]['vars']:
                    self.get_variable(variable)

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
            composer_code = self.run_composer()
            if composer_code == self.dialog.OK:
                if "help" in self.config[self.category]['options'][self.template]:
                    self.dialog_help(url=self.config[self.category]['options'][self.template]['help'])

                self.dialog_exit()


        elif exit_code == self.dialog.HELP:
            self.dialog_help()
            self.main_window()

        elif exit_code == self.dialog.CANCEL:
            self.category_window()

        else:
            self.dialog_exit()


def main():
    base_url = "http://repo.vps.ua/docker/"
    DockerDialog(base_url)

if __name__ == "__main__":
    main()

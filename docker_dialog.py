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
    def __init__(self, base_url):
        self.dialog = Dialog()
        self.dialog.set_background_title("Docker composing")
        self.base_url = base_url
        self.template = ""
        self.template_directory = ""
        self.base_directory = os.path.expanduser("~")
        self.vars = {}
        if self.dialog.yesno("Do you want to create Docker container from the list of preinstalled images?") == self.dialog.DIALOG_OK:
            self.dialog.infobox("Loading list of templates", title="Loading...")
            self.config = yaml.load(urlopen(urljoin(self.base_url, "docker.yml")))
            self.main_window()
        else:
            self.dialog_exit()


    def dialog_exit(self):
        """
        Runned in case of user exit from dialog
        """
        self.dialog.infobox("""Script ends normally.
        You may run this script anytime with command:
        /opt/scripts/docker_dialog.py""",
                            title="Exiting...")
        time.sleep(3)
        os.system('clear')
        # raise SystemExit(0)


    def dialog_help(self):
        """
        Runned in case of user exit from dialog
        """
        
        self.dialog.msgbox("Help text message box",
                              title="Help")
        self.main_window()


    def get_url(self, url):
        """
        Downloads files, which are set in the url section.
        If it's j2 template - parse it and save as .yml in base_directory
        """
        match_jinja = re.match(r"^.*\/(.*)\.j2$", url, re.IGNORECASE)

        try:
            file_from_url = urlopen(urljoin(self.base_url, url)).read()
            if match_jinja:
                final_data = Environment(autoescape=True).from_string(file_from_url).render(self.vars)
                filename = match_jinja.group(1)
            else:
                final_data = file_from_url
                filename = re.match(r"^.*\/(.*)", url).group(1)

            file_destination = open(os.path.join(self.template_directory, filename), 'w')
            file_destination.write(final_data)
            file_destination.close()
        except:
            exit_code = self.dialog.msgbox("Loading failed. Please try installation again", title="Failed!")
            if exit_code == self.dialog.OK:
                self.main_window()
            else:
                self.dialog_exit()
            os.unlink(os.path.join(self.template_directory, filename))


    def get_bundle(self, bundle):
        """
        Downloads bundle and extracts it to the template directory
        """
        bundle_file = re.match(r"^.*\/(.*)", bundle).group(1)
        bundle_path = os.path.join(self.template_directory, bundle_file)
        try:
            urlretrieve(urljoin(self.base_url, bundle), bundle_path)
            if bundle_file.endswith("tar.gz") or bundle_file.endswith(".tgz"):
                tar_archive = tarfile.open(bundle_path)
                tar_archive.extractall(path=self.template_directory)
                tar_archive.close()
        except:
            exit_code = self.dialog.msgbox("Loading failed. Please try installation again", title="Failed!")
            if exit_code == self.dialog.OK:
                self.main_window()
            else:
                self.dialog_exit()
        finally:
            os.unlink(bundle_path)


    def run_composer(self):
        docker_compose = Popen(["docker-compose", "up", "-d"], stdout=PIPE, stderr=PIPE, cwd=self.template_directory)
        code = self.dialog.programbox(fd=docker_compose.stdout.fileno(), text="Installation progress")
        return code

    def get_variable(self, param):
        """
        Asks user to fullfill required variables
        """
        if re.match(r".*password.*", param, re.IGNORECASE):
            exit_code, password1 = self.dialog.passwordbox(
                text="Please, input {0}".format(param),
                insecure=True
                )
            if exit_code == self.dialog.OK:
                exit_code, password2 = self.dialog.passwordbox(
                    text="Please, input {0} one more time".format(param),
                    insecure=True
                    )
                if exit_code == self.dialog.OK:
                    if (password1 == password2) and password1:
                        self.vars.update({param: password2})
                    else:
                        self.dialog.infobox(
                            "Passwords does not match or input was empty. Please, try again",
                            title="Error"
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
            exit_code, value = self.dialog.passwordbox(
                text="Please, input {0}".format(param),
                insecure=True
                )
            if exit_code == self.dialog.OK:
                self.vars.update({param: value})
            elif exit_code == self.dialog.CANCEL:
                self.main_window()
            else:
                self.dialog_exit()


    def main_window(self):
        """
        Window with template selection
        """
        # Generating list of supported templates from the config
        template_tuple = []
        for key, val in self.config.iteritems():
            template_tuple.append((key, val['desc'], val['desc']))


        exit_code, self.template = self.dialog.menu(
            text="Please, select the matching template from the list:",
            choices=template_tuple,
            title="Do you prefer ham or spam?",
            help_button=True,
            item_help=True
            )

        if exit_code == self.dialog.OK:

            self.template_directory = os.path.join(self.base_directory, self.template)

            if not os.path.exists(self.template_directory):
                os.makedirs(self.template_directory)

            # checking if we have vars, that needs to be fullfield by the user
            if self.config[self.template]['vars']:
                for variable in self.config[self.template]['vars']:
                    self.get_variable(variable)

            self.dialog.infobox("Loading composer files", title="Loading...")

            # checking, if we have urls, that needs to be downloaded
            if self.config[self.template]['urls']:
                for url in self.config[self.template]['urls']:
                    self.get_url(url)

            # checking, if we have bundle, that needs to be downloaded
            if self.config[self.template]['bundle']:
                self.get_bundle(self.config[self.template]['bundle'])

            composer_code = self.run_composer()
            if composer_code == self.dialog.OK:
                self.dialog_exit()


        elif exit_code == self.dialog.HELP:
            self.dialog_help()

        else:
            self.dialog_exit()


def main():
    base_url = "http://repo.vps.ua/docker/"
    DockerDialog(base_url)

if __name__ == "__main__":
    main()

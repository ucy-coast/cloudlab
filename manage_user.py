import argparse
import functools
import logging
import sys

from multiprocessing.pool import ThreadPool

import jinja2

import paramiko.client

import xml.etree.ElementTree as ET

log = logging.getLogger(__name__)

xmlns = {'rspec': 'http://www.geni.net/resources/rspec/3'}

def get_hostnames(source):
    """Retrieves hostnames from a manifest file"""
    tree = ET.parse(source)
    root = tree.getroot()
    hostnames = []
    for node in root.findall('rspec:node', xmlns):
        host = node.find('rspec:host', xmlns)
        hostnames.append(host.attrib['name'])
    return hostnames

class ShellCommand:
    def __init__(self, command):
        self.command = command

    def exec(self, hostname, client):
        stdin, stdout, stderr = client.exec_command(self.command)
        if stdout.channel.recv_exit_status():
            for line in stdout.readlines():
                logging.info("%s:%s" % (short_hostname(hostname), line))
            for line in stderr.readlines():
                logging.error("%s:%s" % (short_hostname(hostname), line))
        logging.info("%s:%s" % (short_hostname(hostname), "SUCCESS"))

class ShellCommandFromTemplate(ShellCommand):
    def __init__(self, render_args, template):
        templateLoader = jinja2.FileSystemLoader(searchpath="./")
        templateEnv = jinja2.Environment(loader=templateLoader)
        template = templateEnv.get_template(template)
        command = template.render(**render_args)
        ShellCommand.command = command

class FileTransferCommand:
    def __init__(self, local, remote):
        self.local = local
        self.remote = remote

    def exec(self, hostname, client):
        ftp_client = client.open_sftp()
        ftp_client.put(self.local, self.remote)
        ftp_client.close()

class AddUserAction:
    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('add_user', help = "Add user to test cluster")
        parser.add_argument(
            "-u", "--user", dest='user', required=True,
            help="username of the user")
        parser.add_argument(
            "-k", "--key", dest='ssh_public_key', required=True,
            help="filename of the public key file of the user")
        parser.set_defaults(func=AddUserAction.action)

    @staticmethod
    def action(args):
        hostnames = get_hostnames(args.manifest)

        chain = []
        render_args = {
            'user': args.user,
            'ssh_public_key': ssh_public_key(args.ssh_public_key),
        }
        chain.append(ShellCommandFromTemplate(render_args, "add_user.sh.template.j2"))

        partial_exec_chain = functools.partial(exec_chain, chain, args.admin)
        pool = ThreadPool(4)
        pool.map(partial_exec_chain, hostnames)

class AddUserToK8sAction:
    @staticmethod
    def add_parser(subparsers):
        parser = subparsers.add_parser('add_user_to_k8s', help = "Add user to a Kubernetes cluster")
        parser.add_argument(
            "-u", "--user", dest='user', required=True,
            help="username of the user")
        parser.set_defaults(func=AddUserToK8sAction.action)

    @staticmethod
    def action(args):
        hostnames = get_hostnames(args.manifest)
        for h in hostnames:
            if h.startswith('kubernetes00'):
                hostnames = [h]
                break

        chain = []
        render_args = {
            'user': args.user
        }

        chain.append(ShellCommandFromTemplate(render_args, "add_user_to_k8s.sh.template.j2"))

        partial_exec_chain = functools.partial(exec_chain, chain, args.admin)
        pool = ThreadPool(4)
        pool.map(partial_exec_chain, hostnames)

def parse_args():
    """Configures and parses command-line arguments"""
    parser = argparse.ArgumentParser(
                    prog = 'add_user',
                    description='manager users of a test cluster',
                    formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-l", "--admin", dest='admin', required=True,
        help="login username of the cluster administrator")
    parser.add_argument(
        "-m", "--manifest", dest='manifest', required=True,
        help="filename of the cluster manifest RSpec")
    parser.add_argument(
        "-v", "--verbose", dest='verbose', action='store_true',
        help="verbose")

    subparsers = parser.add_subparsers(dest='subparser_name', help='sub-command help')
    actions = [AddUserAction, AddUserToK8sAction]
    for a in actions:
        a.add_parser(subparsers)

    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s:%(message)s')

    if args.verbose:
        logging.getLogger('').setLevel(logging.INFO)
    else:
        logging.getLogger('').setLevel(logging.ERROR)

    args.func(args)

def ssh_public_key(source):
    with open(source) as f:
        return f.readline()

def short_hostname(hostname):
    return hostname.split('.')[0]

def exec_command(command, admin, hostname):
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    agent = paramiko.Agent()
    agent_keys = agent.get_keys()
    for key in agent_keys:
        try:
            client.connect(hostname, username=admin, pkey=key)
            channel = client.get_transport().open_session()
            stdin, stdout, stderr = client.exec_command(command)
            if stdout.channel.recv_exit_status():
                for line in stderr.readlines():
                    logging.error("%s:%s" % (short_hostname(hostname), line))
            logging.info("%s:%s" % (short_hostname(hostname), "SUCCESS"))
            break
        except Exception as e:
            logging.error(e)

def exec_chain(command_chain, admin, hostname):
    """Executes a chain of commands on a remote host"""
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)

    # setup connection to remote host
    agent = paramiko.Agent()
    agent_keys = agent.get_keys()
    for key in agent_keys:
        try:
            client.connect(hostname, username=admin, pkey=key)
            break
        except Exception as e:
            logging.error(e)
            return

    # execute commands on remote host
    for command in command_chain:
        command.exec(hostname, client)

def real_main():
    parse_args()

def main():
    real_main()
    return
    try:
        real_main()
    except Exception as e:
        logging.error("%s %s" % (e, sys.stderr))
        sys.exit(1)


if __name__ == '__main__':
    main()

import argparse
import tarfile
import os
from os.path import basename
import smtplib
from datetime import datetime
from email.utils import formataddr
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import glob
from typing import List



class NewestFilter:

    @staticmethod
    def supports(filename: str) -> bool:
        rel_filename = os.path.split(filename)[-1].strip()
        if rel_filename.startswith("{") and  rel_filename.endswith("}"):
            return rel_filename.startswith("{%newest.")
        return False

    @staticmethod
    def newest(filename: str) -> List[str]:
        rel_filename = os.path.split(filename)[-1].strip()
        dir = filename[:-len(rel_filename)]
        pattern = "*." + rel_filename[len("{%newest."):-1]
        files = sorted(glob.glob(os.path.join(dir, pattern)), key=lambda f: os.stat(f).st_mtime, reverse=True)
        if len(files) > 0:
            newest_file = files[0]
            print("newest file " + newest_file + " (of " + str(len(files)) + " files)")
            return [newest_file]
        else:
            return []


class Backup:

    def add_entry(self, tar, filename: str, excluded_files: List[str]):
        if os.path.exists(filename):
            if os.path.isfile(filename):
                tar.add(filename)
                print("adding " + filename + " (" + str(round(self.filesize(filename) / 1024)) +  " KB)")
            else:
                for file in os.listdir(filename):
                    self.add_entry(tar, os.path.join(filename, file), excluded_files)
        else:
            print("ignoring " + filename + " (file/dir does not exist)")

    def __build_archive(self, files: List[str], real_name: str):
        tarfile_name = os.path.join(os.getcwd(), real_name + "_backup_" + datetime.now().strftime('%Y-%m-%d') + ".tar.gz")
        with tarfile.open(tarfile_name, mode="w:gz", compresslevel=9) as tf:
            for filename in files:
                print("** " + filename + " **")
                if NewestFilter.supports(filename):
                    for filename in NewestFilter.newest(filename):
                        self.add_entry(tf, filename, [tarfile_name])
                else:
                    self.add_entry(tf, filename,[tarfile_name])
        print(tarfile_name + " created (" + str(round(self.filesize(tarfile_name) / (1024*1024))) +  " MB)")
        return tarfile_name

    def parse_smtp_url(self, smtp_url: str):
        if smtp_url.lower().startswith("smtp://"):
            core = smtp_url[7:]
            user_server_pair = core.split("@")
            user = user_server_pair[0]
            server = user_server_pair[1]
            host = server.split(":")[0]
            port = int(server.split(":")[1])
            return user, host, port
        else:
            raise Exception("unsupported smpt url " + smtp_url)

    def filesize(self, filename) -> int:
        file_stats = os.stat(filename)
        return file_stats.st_size

    def __send_mail(self, tarfile_name: str, smtp_url: str, from_addr: str, to_addr: str, pwd: str, real_name: str, start_tls: bool):
        user, host, port = self.parse_smtp_url(smtp_url)

        try:
            from_with_display = formataddr((real_name, from_addr))
            msg = MIMEMultipart()
            msg['From'] = from_with_display
            msg['To'] = to_addr
            msg['Subject'] = "backup of " + real_name
            msg.attach(MIMEText("please find enclosed the backup of " + real_name))

            with open(tarfile_name, "rb") as fil:
                part = MIMEApplication(fil.read(), Name=basename(tarfile_name))
                part['Content-Disposition'] = 'attachment; filename="%s"' % basename(tarfile_name)
                msg.attach(part)

            smtp_server = smtplib.SMTP(host, port)
            if start_tls:
                smtp_server.starttls()
            smtp_server.ehlo()
            smtp_server.login(user, pwd)
            smtp_server.sendmail(from_with_display, to_addr, msg.as_string())
            smtp_server.close()
            print ("Email sent successfully!")
        except Exception as ex:
            print ("Something went wrong….",ex)


    def build(self,
              files: List[str],
              smtp_url: str,
              from_addr: str,
              to_addr: str,
              pwd: str,
              real_name: str = "backup",
              start_tls: bool = True):
        tarfile_name = None
        try:
            tarfile_name = self.__build_archive(files, real_name)
            self.__send_mail(tarfile_name, smtp_url, from_addr, to_addr, pwd, real_name, start_tls)
        finally:
            if tarfile_name is not None:
                os.remove(tarfile_name)


def main():
    parser = argparse.ArgumentParser(description="Create and send a backup archive.")
    parser.add_argument('-f', '--files', nargs='+', required=True, help='Files or directories to include')
    parser.add_argument('-s', '--smtp', required=True, help='SMTP URL, z.B. smtp://user@host:port')
    parser.add_argument('--from-addr', required=True, dest='from_addr', help='Absenderadresse')
    parser.add_argument('--to-addr', required=True, dest='to_addr', help='Empfängeradresse')
    parser.add_argument('--pwd', required=True, help='SMTP Passwort')
    parser.add_argument('--name', default='backup', help='Anzeigename für das Backup')
    parser.add_argument('--no-starttls', action='store_false', dest='start_tls', help='STARTTLS deaktivieren')
    args = parser.parse_args()

    b = Backup()
    b.build(files=args.files,
            smtp_url=args.smtp,
            from_addr=args.from_addr,
            to_addr=args.to_addr,
            pwd=args.pwd,
            real_name=args.name,
            start_tls=args.start_tls)

if __name__ == '__main__':
    main()

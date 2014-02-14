#!/usr/bin/env python
# encoding: utf-8

import praw
import argparse
import urllib
import os
from imguralbum import *
import re

def get_urls(generator, args):
    urls = []
    for thing in generator:
        if not thing.is_self:
            if thing.over_18 and args.no_nsfw:
                continue
            if thing.score < args.score:
                continue
            if thing.url not in urls and "imgur.com" in thing.url:
                urls.append(thing.url)
    return urls

def download_images(url, args):
    # Check if it's an album
    try:
        downloader = ImgurAlbumDownloader(url)

        if not args.quiet:
            def image_progress(index, image_url, dest):
                print "Downloading image {} of {} from album {} to {}".format(index, downloader.num_images(), url, dest)

            downloader.on_image_download(image_progress)
        downloader.save_images(args.output)
    except ImgurAlbumException as e:
        # Not an album, unfortunately.
        # or some strange error happened.
        if not e.msg.startswith("URL"):
            print e.msg
            return

        # Check if it's a silly url.
        m = re.match(r"(?:https?\:\/\/)?(?:www\.)?imgur\.com\/([a-zA-Z0-9]+)", url)
        image = ''
        image_url = ''
        if m:
            # we don't know the extension
            # so we have to rip it from the url
            # by reading the HTML, unfortunately.
            response = urllib.urlopen(url)
            if response.getcode() != 200:
                print "Image download failed: HTML response code {}".format(response.getcode())
                return

            html = response.read()
            image = re.search('<img src="(\/\/i\.imgur\.com\/([a-zA-Z0-9]+\.(?:jpg|jpeg|png|gif)))"', html)
            if image:
                image_url = "http:" + image.group(1)
        else:
            image = re.match(r'(https?\:\/\/)?(?:www\.)?i\.imgur\.com\/([a-zA-Z0-9]+\.(?:jpg|jpeg|png|gif))', url)
            if image:
                image_url = image.group(0)


        if not image_url:
            print "Image url {} could not be properly parsed.".format(url, image)
            return

        if not os.path.exists(args.output):
            os.makedirs(args.output)

        p = os.path.join(args.output, image.group(2))

        if not args.quiet:
            print "Downloading image {} to {}".format(image_url, p)

        urllib.urlretrieve(image_url, p)





def redditor_retrieve(r, args):
    user = r.get_redditor(args.username)
    gen = user.get_submitted(limit=args.limit)

    links = get_urls(gen, args)
    for link in links:
        download_images(link, args)

def subreddit_retrieve(r, args):
    sub = r.get_subreddit(args.subreddit)
    method = getattr(sub, "get_{}".format(args.sort))
    gen = method(limit=args.limit)
    links = get_urls(gen, args)
    for link in links:
        download_images(link, args)

if __name__ == "__main__":
    user_agent = "Image retriever 1.0.0 by /u/Rapptz"
    r = praw.Reddit(user_agent=user_agent)
    parser = argparse.ArgumentParser(description="Downloads imgur images from a user and/or subreddit.",
                                     usage="%(prog)s [options...]")
    parser.add_argument("--username", help="username to scrap and download from", metavar="user")
    parser.add_argument("--subreddit", help="subreddit to scrap and download from", metavar="sub")
    parser.add_argument("--sort", help="Choose the sort order for subreddit submissions", 
                                  choices=["hot", "new", "controversial", "top"], metavar="type", default="hot")
    parser.add_argument("--limit", type=int, help="number of reddit submissions to look for", default=100, metavar="num")
    parser.add_argument("-q", "--quiet", action="store_true", help="doesn't print image download progress")
    parser.add_argument("-o", "--output", help="where to output the downloaded images", metavar="")
    parser.add_argument("--no-nsfw", action="store_true", help="only downloads images not marked nsfw")
    parser.add_argument("--score", help="minimum score of the image to download", type=int, metavar="num", default=1)

    args = parser.parse_args()

    if args.username:
        redditor_retrieve(r, args)

    if args.subreddit:
        subreddit_retrieve(r, args)
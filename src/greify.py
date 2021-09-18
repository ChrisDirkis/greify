from pathlib import Path
from shutil import rmtree, copytree
from itertools import product

import sass

import json
import re
import markdown


build_folder = "build"
site_folder = "site"

posts_folder = "posts"
templates_folder = "templates"
public_folder = "public"

post_template_filename = "post.html"
home_template_filename = "home.html"
post_link_template_filename = "post_link.html"


def load_posts(site_path):
    posts_path = site_path / posts_folder
    posts = [load_post(metadata_path) for metadata_path in posts_path.glob("**/metadata.json")] if posts_path.exists() else []
    posts = [post for post in posts if post]
    posts.sort(key=lambda post: post["datetime"], reverse=True)

    # validate slugs (n^2, could be n^2/2)
    for a, b in product(posts, repeat=2):
        if a is not b and a["slug"] == b["slug"]:
            raise Exception(f"Two posts share the same slug ({a['slug']})")

    # add next and prev slug links
    for i in range(len(posts)):
        post = posts[i]
        if i > 0:
            post["next"] = posts[i - 1]["slug"]
        if i < len(posts) - 1:
            post["prev"] = posts[i + 1]["slug"]

    return posts


def load_post(metadata_path):
    with open(metadata_path) as metadata_file:
        metadata = json.load(metadata_file)
        metadata["path"] = metadata_path
        if not ("draft" in metadata and metadata["draft"]):
            return metadata


def generate_post_page(post, build_path, post_template):
    page_folder_path = build_path / post["slug"]
    post_path = post["path"].parent

    # make the dir, populate with public stuff
    public_path = post_path / "public"
    if public_path.exists():
        copytree(public_path, page_folder_path)
    else:  
        page_folder_path.mkdir()

    post_markdown_path = post_path / "post.md"
    post_markdown = post_markdown_path.read_text()
    post_markdown = re.sub(r"!\{(.*)\}", f"/{post['slug']}/" + r"\1", post_markdown)

    post_html = markdown.markdown(post_markdown)

    page_html = re.sub(r"!\{content\}", post_html, post_template)

    for element in ["title", "datetime"]:
        if post[element]:
            page_html = re.sub(r"!\{" + element + r"\}", post[element], page_html)

    for element in ["header_image"]:
        if post[element]:
            page_html = re.sub(r"!\{" + element + r"\}", f"/{post['slug']}/{post[element]}", page_html)

    if "prev" in post:
        prev_element = f"<a href='/{post['prev']}'>Previous</a>"
        page_html = re.sub(r"!\{prev\}", prev_element, page_html)
    else:
        page_html = re.sub(r"!\{prev\}", "", page_html)

    if "next" in post:
        next_element = f"<a href='/{post['next']}'>Next</a>"
        page_html = re.sub(r"!\{next\}", next_element, page_html)
    else:
        page_html = re.sub(r"!\{next\}", "", page_html)
        
    page_path = page_folder_path / "index.html"
    page_path.write_text(page_html)


def generate_post_link(post, post_link_template):
    post_link = post_link_template

    for element in ["title", "datetime", "slug"]:
        if post[element]:
            post_link = re.sub(r"!\{" + element + r"\}", post[element], post_link)

    for element in ["header_image"]:
        if post[element]:
            post_link = re.sub(r"!\{" + element + r"\}", f"/{post['slug']}/{post[element]}", post_link)

    return post_link

def generate_home_page(posts, build_path, home_template, post_link_template):
    home_html = home_template

    post_links = "".join(generate_post_link(post, post_link_template) for post in posts)
    home_html = re.sub(r"!\{post_links\}", post_links, home_html)

    home_path = build_path / "index.html"
    home_path.write_text(home_html)

def initialise_build_folder(site_path, build_path):
    # conveniently, copytree creates the dir at build_path
    copytree(site_path / public_folder, build_path)


def clear_old_build():
    build_path = Path(build_folder)
    if build_path.exists():
        rmtree(build_path)


def build():
    site_path = Path(site_folder)
    if not site_path.exists():
        raise Exception("No site to build")

    build_path = Path(build_folder)
    initialise_build_folder(site_path, build_path)

    for scss_path in (site_path / templates_folder).glob("*.scss"):
        css_path = build_path / scss_path.with_suffix(".css").name
        css = sass.compile(string=scss_path.read_text())
        css_path.write_text(css)

    posts = load_posts(site_path)
    post_template_path = site_path / templates_folder / post_template_filename
    post_template = post_template_path.read_text()

    for post in posts:
        generate_post_page(post, build_path, post_template)


    home_template_path = site_path / templates_folder / home_template_filename
    home_template = home_template_path.read_text()

    post_link_template_path = site_path / templates_folder / post_link_template_filename
    post_link_template = post_link_template_path.read_text()

    generate_home_page(posts, build_path, home_template, post_link_template)
    

def main():
    clear_old_build()
    build()


if __name__ == "__main__":
    main()
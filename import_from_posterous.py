from bs4 import BeautifulSoup
from html2text import html2text

import sys
import datetime
import os
import json

from simple import db, Post

def read_to_post(src_path):
	with open(src_path, 'r') as f:
		soup = BeautifulSoup(f)
		header = soup.find_all('div', class_='post_header')[0]
		body = soup.find_all('div', class_='post_body')[0]
		post_time_str = ' '.join(header.find('span', class_="post_time").string.split())
		post_time = datetime.datetime.strptime(post_time_str, '%B %d %Y, %I:%M %p')
		title = header.find('h3').string.strip()

		post = Post(title = title, created_at = post_time)

		embed = body.find('div', class_='p_audio_embed')
		if embed:
			href = embed.a.get('href')
			href = '/uploads/posterous' + href[href.find('/audio/'):]
			mp3 = soup.new_tag('a', href=href)
			mp3.attrs['class'] = 'sm2_button'
			mp3.string = 'Listen'
			embed.a.replace_with(mp3)

		src_name,_ = os.path.splitext(os.path.basename(src_path))
		post.readable_id = post.readable_id + src_name

		#must set this so that set_content() can detect links (for has_audio)
		#if not set, it doesn't convert to html first... so links is []
		post.text_type = 'markdown' 
	
		post.set_content(html2text(unicode(body)))
		post.draft = False
		return post



src_dir = sys.argv[1]

for dir_path, dirs, files in os.walk(src_dir):
	for file_name in files:
		if file_name.endswith('.html'):
			file_path = os.path.join(dir_path, file_name)
			post = read_to_post(file_path)
			print(post.readable_id)
			db.session.add(post)
db.session.commit()

#! /usr/bin/python
# Only external dependency should be BeautifulSoup
# Originally required numpy but shouldn't anymore

import urllib2, csv, re, pickle
#import numpy as np
from bs4 import BeautifulSoup
from collections import Counter

BASE = 'http://web.pdc.wa.gov'	# Domain to be searched
HOME = '/MvcQuerySystem/Candidate/sw_candidates'	# Url to start on; deprecated
PAGEFILE = 'pagenames.txt'	# List of pages on the domain to be searched; contains URLs for subtypes of candidate/committee/lobbyist
OUTPUT = 'results.csv'	# Where to save results

# Counts invalid characters we've filtered out
UNICOUNT = Counter()

def cleanwrite(row, writer):
	if row == [u'No records to display.']: return
	try:
		writer.writerow(row)
	# Filter out anything we can't encode as utf-8
	except UnicodeEncodeError:
		rowstring = ''.join(row)
		weirdchars = filter(lambda x: ord(x) not in range(128), rowstring)
		for c in weirdchars:
			UNICOUNT.update(c)
		cleanrowtext = [cell.encode('utf-8','ignore') for cell in row]
		writer.writerow(cleanrowtext)


def writetable(table, writer, prefix=[]):
	try:
		for row in table.find('tbody').findAll('tr'):
			rowtext = prefix+[cell.text for cell in row.findAll('td')]
			cleanwrite(rowtext, writer)
	# Sometimes there wasn't really a table on the page; if so, don't write
	except AttributeError as a:
		print '\t\t',
		print a
		pass

def grab(url, writer, prefix=[]):
	u = urllib2.urlopen(url)
	s = BeautifulSoup(u.read(), 'html.parser')
	table = s.find(id='grid1')
	try:
		endpage = s.find('span', {'class': 't-icon t-arrow-last'}).parent.get('href')
		matches = re.search(r'(.+page=)(\d+)', endpage)
		stem, index = matches.group(1), int(matches.group(2))
	# If there's only one page in this series, just write the current page
	except AttributeError:
		writetable(table, writer,prefix)
		return
	# Else iterate through all pages
	for i in range(1, index+1):
#		print '\t\t\t'+url+stem+str(i)
		u = urllib2.urlopen(BASE+stem+str(i))
		s = BeautifulSoup(u.read(), 'html.parser')
		table = s.find(id='grid1')
		writetable(table, writer,prefix)


# Get details on a candidate/committee/lobbyist from the top-level list
def getdetails(url, writer, prefix=[]):
	u = urllib2.urlopen(url)
	s = BeautifulSoup(u.read(), 'html.parser')
	types = s.find(id='menu')
	if types:
		for sub_addr in types.findAll('a'):
			prefix.append(sub_addr.text)
#			print '\t\t%s'%sub_addr.text
			link = sub_addr.get('href')
#			print '\t\t%s'%BASE+link
			grab(BASE+link, writer, prefix)
	else:
		grab(url, writer,prefix)


def main():
	pages = [line.strip() for line in open(PAGEFILE)]
	u = urllib2.urlopen(BASE+HOME)
	soup_home = BeautifulSoup(u.read(), 'html.parser')
	w = csv.writer(open(OUTPUT, 'a'))
	# Loop over types of elections
	for url in pages:
		level1 = url.split('/')[-1]
		u_start = urllib2.urlopen(BASE+url)
		soup_start = BeautifulSoup(u_start.read(), 'html.parser')
		yearlist = [int(y.text) for y in soup_start.find(id='YearList').find_all('option')]
		# Loop over years available
		for year in yearlist:
			u_s = urllib2.urlopen('%s%s?year=%d' % (BASE,url,year))
			print '%s%s?year=%d' % (BASE,url,year)
			soup_s = BeautifulSoup(u_s.read(), 'html.parser')
			table = soup_s.find(id='grid1')
			endpage = soup_s.find('span', {'class': 't-icon t-arrow-last'}).parent.get('href')
			matches = re.search(r'(.+page=)(\d+)', endpage)
			# Catch error if only one page
			try:
				stem, index = matches.group(1), int(matches.group(2))
				# Iterate through all pages
				for i in range(1,index+1):
					print '\t'+str(i)
					u_s = urllib2.urlopen(BASE+stem+str(i))
					soup_s = BeautifulSoup(u_s.read(), 'html.parser')
					table = soup_s.find(id='grid1')
					for row in table.find('tbody').findAll('tr'):
						# Write row in this table
						cleanwrite([level1,str(year)]+[cell.text for cell in row.findAll('td')], w)
						# Get further data on this candidate/committee/lobbyist
						detlink = row.find('a')
						try:
							getdetails(BASE+detlink.get('href'), w, [level1,str(year)])
						except urllib2.HTTPError:
							continue
			# Handles the one-page case just like above
			except AttributeError:
				table = soup_s.find(id='grid1')
				for row in table.find('tbody').findAll('tr'):
					cleanwrite([level1,str(year)]+[cell.text for cell in row.findAll('td')], w)
					detlink = row.find('a')
					try:
						getdetails(BASE+detlink.get('href'), w, [level1,str(year)])
					except urllib2.HTTPError:
						continue
			print ''
	print 'Done with processing!'
	# Sanity check that we only filtered out weird characters.
	print 'Ignored characters:'
	for k,v in sorted(UNICOUNT.items(), key=lambda x: -x[1]):
		print k,v


if __name__ == '__main__': main()
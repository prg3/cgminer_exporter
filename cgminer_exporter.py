#!/usr/bin/env python2.7

# Copyright 2013 Setkeh Mkfr
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.  See COPYING for more details.

#Short Python Example for connecting to The Cgminer API
#Written By: setkeh <https://github.com/setkeh>
#Thanks to Jezzz for all his Support.
#NOTE: When adding a param with a pipe | in bash or ZSH you must wrap the arg in quotes
#E.G "pga|0"

import socket
import os
import json
import sys
import pprint
import datetime
import tornado
import tornado.web
import tornado.options

pp = pprint.PrettyPrinter(indent=4)


statusdata = {}

if os.environ.get('THREADS'):
	threads = int(os.environ['THREADS'])
else:
	threads = 0
	

def linesplit(socket):
	buffer = socket.recv(4096)
	done = False
	while not done:
		more = socket.recv(4096)
		if not more:
			done = True
		else:
			buffer = buffer+more
	if buffer:
		return buffer

def getfromIP(ip):
	data = {}
	for func in [ 'stats', 'version', 'pools', 'summary', 'devs' ]:
		s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		s.settimeout(1)
		s.connect((ip,int(4028)))
		data[func] = getfunction(s, func)
		s.close()
	return data

def getfunction(s, function):
	s.send(json.dumps({"command":function}))
	response = linesplit(s)
	response = response.replace('\x00','')
	response = response.replace('}{','},{')
	return(json.loads(response))

class HelpHandler(tornado.web.RequestHandler):
	def get(self):
		self.write( "Use /metrics with ?target=IP\n")

class MetricsHandler(tornado.web.RequestHandler):
	def get(self):
		target=self.get_argument("target", None, True)
		metricdata = getfromIP(target)
		if 'CGMiner' in metricdata['version']['VERSION'][0]:
			tags = 'instance="%s",cgminer_version="%s",api_version="%s",type="%s",miner="%s"'%(target,metricdata['version']['VERSION'][0]['CGMiner'],metricdata['version']['VERSION'][0]['API'],metricdata['version']['VERSION'][0]['Type'],metricdata['version']['VERSION'][0]['Miner'])
		elif 'BMMiner' in metricdata['version']['VERSION'][0]:
			tags = 'instance="%s",bmminer_version="%s",api_version="%s",type="%s",miner="%s"'%(target,metricdata['version']['VERSION'][0]['BMMiner'],metricdata['version']['VERSION'][0]['API'],metricdata['version']['VERSION'][0]['Type'],metricdata['version']['VERSION'][0]['Miner'])
		else:
			tags = 'instance="%s",api_version="%s",type="%s",miner="%s"'%(target,metricdata['version']['VERSION'][0]['API'],metricdata['version']['VERSION'][0]['Type'],metricdata['version']['VERSION'][0]['Miner'])
		self.write("#CGMiner metrics export\n")
		for type in metricdata:
			if type == "pools":
				self.write(metric_pool(metricdata[type], tags))
			elif type == "summary":
				self.write(metric_summary(metricdata[type], tags))
			elif type == "stats":
				self.write(metric_stats(metricdata[type], tags))

def metric_pool(data, tags):
	string = "# Pools Data\n"
	string += "cgminer_pool_count{%s} %s\n"%(tags, len(data['POOLS']))
	for pool in data['POOLS']:
		localtags = 'pool="%s",url="%s",stratum_url="%s",%s'%(pool['POOL'], pool['URL'], pool['Stratum URL'], tags)
		string += 'cgminer_pool_diff_accepted{%s} %s\n'%(localtags, pool['Difficulty Accepted'])
		string += 'cgminer_pool_rejected{%s} %s\n'%(localtags, pool['Difficulty Accepted'])
		string += 'cgminer_pool_diff_rejected{%s} %s\n'%(localtags, pool['Difficulty Rejected'])
		string += 'cgminer_pool_stale{%s} %s\n'%(localtags, pool['Stale'])
		try:
			[hr, mn, ss] = [int(x) for x in pool['Last Share Time'].split(':')]
			sharetime = datetime.timedelta(hours=hr, minutes=mn, seconds=ss).seconds
		except:
			sharetime = 0
		string += 'cgminer_pool_last_share{%s} %s\n'%(localtags, sharetime)
		string += 'cgminer_pool_getworks{%s} %s\n'%(localtags, pool['Getworks'])
		string += 'cgminer_pool_last_diff{%s} %s\n'%(localtags, pool['Last Share Difficulty'])
		if pool['Status'] == "Alive":
			status = 1
		else:
			status = 0
		string += 'cgminer_pool_status{%s} %s\n'%(localtags, status)
		if pool['Stratum Active']:
			active = 1
		else:
			active = 0
		string += 'cgminer_pool_stratum_active{%s} %s\n'%(localtags, active)
	return (string)

def metric_summary(data, tags):
	string = "#Pool Summary\n"
	localtags = tags
	string += 'cgminer_summary_rejected{%s} %s\n'%(localtags, data['SUMMARY'][0]['Rejected'])
	string += 'cgminer_summary_found_blocks{%s} %s\n'%(localtags, data['SUMMARY'][0]['Found Blocks'])
	string += 'cgminer_summary_elapsed{%s} %s\n'%(localtags, data['SUMMARY'][0]['Elapsed'])
	string += 'cgminer_summary_hardware_errors{%s} %s\n'%(localtags, data['SUMMARY'][0]['Hardware Errors'])
	string += 'cgminer_summary_total_mh{%s} %s\n'%(localtags, data['SUMMARY'][0]['Total MH'])
	string += 'cgminer_summary_ghs_average{%s} %s\n'%(localtags, data['SUMMARY'][0]['GHS av'])
	string += 'cgminer_summary_ghs_5s{%s} %s\n'%(localtags, data['SUMMARY'][0]['GHS 5s'])

	return (string)

#def metric_stats(data, tags):
#	string = "# Stats\n"
#	if data['STATS'][0]['Type'] == "Antminer L3+":
#		string += metric_summary_s9(data, tags, string)
#	if data['STATS'][0]['Type'] == "Antminer S9":
#		string += metric_summary_s9(data, tags, string)
#
#	return (string)
#
#def metric_summary_l3plus(data, tags, string):
#	statdata = data['STATS'][1]
#	localtags = '%s'%(tags)
#	for i in [1, 2, 3, 4]:
#		string += 'cgminer_stats_chain_rate{chain="%s",%s} %s\n'%(i, localtags, statdata['chain_rate%s'%(i)])
#		string += 'cgminer_stats_chain_acn{chain="%s",%s} %s\n'%(i, localtags, statdata['chain_acn%s'%(i)])
#		string += 'cgminer_stats_chain_hw{chain="%s",%s} %s\n'%(i, localtags, statdata['chain_hw%s'%(i)])
#	for i in [1,2]:
#		string += 'cgminer_stats_fan{fan="%s",%s} %s\n'%(i, localtags, statdata['fan%s'%(i)])
#	for i in ['1','2_1','2_2','2_3','2_4','31','32','33','34','4_1','4_2','4_3','4_4']:
#		string += 'cgminer_stats_temp{temp="%s",%s} %s\n'%(i, localtags, statdata['temp%s'%(i)])
#		
#	string += 'cgminer_stats_frequency{%s} %s\n'%(localtags, statdata['frequency'])
#	
#	return (string)

def metric_stats(data, tags):
	string = "# Stats\n"
	statdata = data['STATS'][1]
	localtags = '%s'%(tags)
	for entry in statdata:
		if 'temp' in entry:
			tempnum = entry.replace("temp","")
			string += 'cgminer_stats_temp{temp="%s",%s} %s\n'%(tempnum, localtags, statdata['temp%s'%(tempnum)])
		if 'chain_hw' in entry:
			chainnum = entry.replace("chain_hw","")
			if statdata['chain_rate%s'%(chainnum)]:
				string += 'cgminer_stats_chain_rate{chain="%s",%s} %s\n'%(chainnum, localtags, statdata['chain_rate%s'%(chainnum)])
			else:
				string += 'cgminer_stats_chain_rate{chain="%s",%s} %s\n'%(chainnum, localtags, 0)
			string += 'cgminer_stats_chain_acn{chain="%s",%s} %s\n'%(chainnum, localtags, statdata['chain_acn%s'%(chainnum)])
			string += 'cgminer_stats_chain_hw{chain="%s",%s} %s\n'%(chainnum, localtags, statdata['chain_hw%s'%(chainnum)])
		if 'fan' in entry:
			fannum = entry.replace("fan","")
			string += 'cgminer_stats_fan{fan="%s",%s} %s\n'%(fannum, localtags, statdata['fan%s'%(fannum)])
		if 'freq_avg' in entry:
			freqnum = entry.replace("freq_avg","")
			string += 'cgminer_stats_freq{freq="%s",%s} %s\n'%(freqnum, localtags, statdata['freq_avg%s'%(freqnum)])

	string += 'cgminer_stats_frequency{%s} %s\n'%(localtags, statdata['frequency'])

	return (string)

def main():
	tornado.options.parse_command_line()
	application = tornado.web.Application([
		(r"/", HelpHandler),
		(r"/metrics", MetricsHandler)

	])
	http_server = tornado.httpserver.HTTPServer(application, idle_connection_timeout=2)
	http_server.bind(9154)
	http_server.start(threads)
	tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
	main()

#!/usr/bin/env python3

import asyncio
import socket
import os
import json
import pprint
import datetime
import tornado

pp = pprint.PrettyPrinter(indent=4)

statusdata = {}

threads = int(os.environ.get("THREADS", 0))


def linesplit(socket):
    buffer = socket.recv(4096)
    done = False
    while not done:
        more = socket.recv(4096)
        if not more:
            done = True
        else:
            buffer += more
    if buffer:
        return buffer


def getfromIP(ip):
    data = {}
    for func in ["stats", "version", "pools", "summary", "devs"]:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.connect((ip, 4028))
        data[func] = getfunction(s, func)
        s.close()
    return data


def getfunction(s, function):
    s.sendall(json.dumps({"command": function}).encode("utf-8"))
    response = linesplit(s)
    response = response.replace(b"\x00", b"").decode("utf-8")
    response = response.replace("}{", "},{")
    return json.loads(response)


class HelpHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("Use /metrics with ?target=IP\n")


class MetricsHandler(tornado.web.RequestHandler):
    def get(self):
        target = self.get_argument("target", None, True)
        metricdata = getfromIP(target)
        if "CGMiner" in metricdata["version"]["VERSION"][0]:
            tags = (
                'instance="%s",cgminer_version="%s",api_version="%s",type="%s",miner="%s"'
                % (
                    target,
                    metricdata["version"]["VERSION"][0]["CGMiner"],
                    metricdata["version"]["VERSION"][0]["API"],
                    metricdata["version"]["VERSION"][0]["Type"],
                    metricdata["version"]["VERSION"][0]["Miner"],
                )
            )
        elif "BMMiner" in metricdata["version"]["VERSION"][0]:
            tags = (
                'instance="%s",bmminer_version="%s",api_version="%s",type="%s",miner="%s"'
                % (
                    target,
                    metricdata["version"]["VERSION"][0]["BMMiner"],
                    metricdata["version"]["VERSION"][0]["API"],
                    metricdata["version"]["VERSION"][0]["Type"],
                    metricdata["version"]["VERSION"][0]["Miner"],
                )
            )
        else:
            tags = 'instance="%s",api_version="%s",type="%s",miner="%s"' % (
                target,
                metricdata["version"]["VERSION"][0]["API"],
                metricdata["version"]["VERSION"][0]["Type"],
                metricdata["version"]["VERSION"][0]["Miner"],
            )
        self.write("#CGMiner metrics export\n")
        for type in metricdata:
            if type == "pools":
                self.write(metric_pool(metricdata[type], tags))
                self.write("\n")
            elif type == "summary":
                self.write(metric_summary(metricdata[type], tags))
                self.write("\n")
            elif type == "stats":
                self.write(metric_stats(metricdata[type], tags))
                self.write("\n")


def metric_pool(data, tags):
    lines = ["# Pools Data"]
    lines.append(f"cgminer_pool_count{{{tags}}} {len(data['POOLS'])}")
    for pool in data["POOLS"]:
        localtags = f'pool="{pool["POOL"]}",url="{pool["URL"]}",stratum_url="{pool["Stratum URL"]}",{tags}'
        lines.append(
            f'cgminer_pool_diff_accepted{{{localtags}}} {pool["Difficulty Accepted"]}'
        )
        lines.append(
            f'cgminer_pool_rejected{{{localtags}}} {pool["Difficulty Accepted"]}'
        )
        lines.append(
            f'cgminer_pool_diff_rejected{{{localtags}}} {pool["Difficulty Rejected"]}'
        )
        lines.append(f'cgminer_pool_stale{{{localtags}}} {pool["Stale"]}')
        try:
            hr, mn, ss = [int(x) for x in pool["Last Share Time"].split(":")]
            sharetime = datetime.timedelta(hours=hr, minutes=mn, seconds=ss).seconds
        except:
            sharetime = 0
        lines.append(f"cgminer_pool_last_share{{{localtags}}} {sharetime}")
        lines.append(f'cgminer_pool_getworks{{{localtags}}} {pool["Getworks"]}')
        lines.append(
            f'cgminer_pool_last_diff{{{localtags}}} {pool["Last Share Difficulty"]}'
        )
        status = 1 if pool["Status"] == "Alive" else 0
        lines.append(f"cgminer_pool_status{{{localtags}}} {status}")
        active = 1 if pool["Stratum Active"] else 0
        lines.append(f"cgminer_pool_stratum_active{{{localtags}}} {active}")
    return "\n".join(lines)


def metric_summary(data, tags):
    lines = ["#Pool Summary"]
    localtags = tags
    lines.append(
        f'cgminer_summary_rejected{{{localtags}}} {data["SUMMARY"][0]["Rejected"]}'
    )
    lines.append(
        f'cgminer_summary_found_blocks{{{localtags}}} {data["SUMMARY"][0]["Found Blocks"]}'
    )
    lines.append(
        f'cgminer_summary_elapsed{{{localtags}}} {data["SUMMARY"][0]["Elapsed"]}'
    )
    lines.append(
        f'cgminer_summary_hardware_errors{{{localtags}}} {data["SUMMARY"][0]["Hardware Errors"]}'
    )
    lines.append(
        f'cgminer_summary_total_mh{{{localtags}}} {data["SUMMARY"][0]["Total MH"]}'
    )
    lines.append(
        f'cgminer_summary_ghs_average{{{localtags}}} {data["SUMMARY"][0]["GHS av"]}'
    )
    lines.append(
        f'cgminer_summary_ghs_5s{{{localtags}}} {data["SUMMARY"][0]["GHS 5s"]}'
    )
    return "\n".join(lines)


def metric_stats(data, tags):
    lines = ["# Stats"]
    statdata = data["STATS"][1]
    localtags = f"{tags}"
    for entry in statdata:
        if "temp" in entry:
            tempnum = entry.replace("temp", "")
            lines.append(
                f'cgminer_stats_temp{{temp="{tempnum}",{localtags}}} {statdata[f"temp{tempnum}"]}'
            )
        if "chain_hw" in entry:
            chainnum = entry.replace("chain_hw", "")
            if statdata[f"chain_rate{chainnum}"]:
                lines.append(
                    f'cgminer_stats_chain_rate{{chain="{chainnum}",{localtags}}} {statdata[f"chain_rate{chainnum}"]}'
                )
            else:
                lines.append(
                    f'cgminer_stats_chain_rate{{chain="{chainnum}",{localtags}}} 0'
                )
            lines.append(
                f'cgminer_stats_chain_acn{{chain="{chainnum}",{localtags}}} {statdata[f"chain_acn{chainnum}"]}'
            )
            lines.append(
                f'cgminer_stats_chain_hw{{chain="{chainnum}",{localtags}}} {statdata[f"chain_hw{chainnum}"]}'
            )
        if "fan" in entry:
            fannum = entry.replace("fan", "")
            lines.append(
                f'cgminer_stats_fan{{fan="{fannum}",{localtags}}} {statdata[f"fan{fannum}"]}'
            )
        if "freq_avg" in entry:
            freqnum = entry.replace("freq_avg", "")
            lines.append(
                f'cgminer_stats_freq{{freq="{freqnum}",{localtags}}} {statdata[f"freq_avg{freqnum}"]}'
            )
    lines.append(f'cgminer_stats_frequency{{{localtags}}} {statdata["frequency"]}')
    return "\n".join(lines)


async def main():
    tornado.options.parse_command_line()
    app = tornado.web.Application([(r"/", HelpHandler), (r"/metrics", MetricsHandler)])
    app.listen(9154)
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

# What is this ?
We had to estimate how much the network interface was utilized for our cluster. We tried to use the telgraf input plugin called "net", however it only gives bytes/packets transmitted/received at a given time, not estimated bandwidth. The bandwidth had to be estimated in grafana using the non_negative_derivate() but that did noy behave nicely when used with multiple hosts.
We created this script instead, that estimates the network usage in percent ((recv_bytes-last_recv_bytes)/interface speed). The resulting bandwidth (both tx and rx) is written to a file stored in /tmp, which is then read by telegraf's file-input plugin.

## Usage
```
python3 telegraf_input_plugin_bw.py <interface name>
```
Add the following lines to /etc/teleraf/telegraf.conf
```
[[inputs.file]]
    files = ["/tmp/telegraf_bandwidth_collector"]
    data_format = "influx"

```

## Example influxdb query in grafana
```
SELECT mean("bw_rx_percent") FROM "autogen"."custom_net" WHERE ("host" =~ /^$Server$/) AND $timeFilter GROUP BY time($myinterval) fill(null)
```

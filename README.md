# cgminer_exporter
Prometheus exporter for Cgminer (specifically Antminers)

Configuration Example

Setup the targets array with your miners, and set the replacement line to the host running the exporter

'''YAML
- job_name: 'antminer'
    scrape_interval: 2s
    static_configs:
      - targets: ['192.168.0.21', '192.168.0.22', '192.168.0.23', '192.168.0.24']
    metrics_path: /metrics
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: 192.168.0.190:9154
'''

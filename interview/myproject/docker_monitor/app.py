from flask import Flask, render_template
import docker

app = Flask(__name__)
client = docker.from_env()

@app.route('/')
def index():
    containers = client.containers.list()
    container_stats = []
    for container in containers:
        stats = container.stats(stream=False)
        container_stats.append({
            'name': container.name,
            'cpu_usage': stats['cpu_stats']['cpu_usage']['total_usage'],
            'memory_usage': stats['memory_stats']['usage'],
            'network_rx': stats['networks']['eth0']['rx_bytes'],
            'network_tx': stats['networks']['eth0']['tx_bytes']
        })
    return render_template('index.html', container_stats=container_stats)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

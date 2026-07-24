#!/usr/bin/env bash
# 给运行中的 kind 节点配 GPU 直通(CDI 路线,零宿主全局改动)。
# 幂等:可重复跑。前提:宿主已装 nvidia-container-toolkit + driver,已生成 /etc/cdi/nvidia.yaml。
set -euo pipefail
N=pp-split-control-plane
export PATH="$HOME/.local/bin:$PATH"

echo "[1/5] 拷 nvidia toolkit 二进制进节点"
for b in nvidia-ctk nvidia-container-runtime nvidia-container-runtime-hook nvidia-container-cli; do
  docker cp /usr/bin/$b $N:/usr/bin/$b
done
docker cp /usr/bin/../lib/x86_64-linux-gnu/libnvidia-container.so.1 $N:/usr/lib/x86_64-linux-gnu/libnvidia-container.so.1 2>/dev/null || true

echo "[2/5] 拷 CDI spec + 全部 driver 库/二进制进节点(照 CDI spec hostPath 清单)"
docker exec $N mkdir -p /etc/cdi
docker cp /etc/cdi/nvidia.yaml $N:/etc/cdi/nvidia.yaml
PATHS=$(grep -oE 'hostPath: \S+' /etc/cdi/nvidia.yaml | awk '{print $2}' | sort -u | grep -vE '^/dev/|socket$')
for p in $PATHS; do
  [ -e "$p" ] || continue
  docker exec $N mkdir -p "$(dirname "$p")" 2>/dev/null || true
  docker cp "$p" $N:"$p" 2>/dev/null || true
done
docker exec $N ldconfig

echo "[3/5] 配节点内 containerd: 启用 nvidia runtime + CDI"
docker exec $N nvidia-ctk runtime configure --runtime=containerd --cdi.enabled
docker exec $N systemctl restart containerd
sleep 6
kubectl wait --for=condition=Ready node/$N --timeout=90s

echo "[4/5] 建 nvidia RuntimeClass + 装 device-plugin(用 nvidia runtimeClass)"
kubectl apply -f - <<'YAML'
apiVersion: node.k8s.io/v1
kind: RuntimeClass
metadata: { name: nvidia }
handler: nvidia
YAML
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.17.1/deployments/static/nvidia-device-plugin.yml 2>/dev/null || true
kubectl -n kube-system patch daemonset nvidia-device-plugin-daemonset --type merge \
  -p '{"spec":{"template":{"spec":{"runtimeClassName":"nvidia"}}}}'
kubectl -n kube-system rollout status daemonset/nvidia-device-plugin-daemonset --timeout=120s

echo "[5/5] 验证节点上报 GPU"
sleep 10
echo "nvidia.com/gpu = $(kubectl get node $N -o jsonpath='{.status.allocatable.nvidia\.com/gpu}')"

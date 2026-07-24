# Pitfalls & hard-won fixes

Every item here was hit and fixed during a real 7-GPU run. Symptoms are what you
actually see; root causes are verified, not guessed.

## 1. docker-kill hang aborts the whole orchestration

**Symptom.** On a topology switch, the orchestrator dies with:
```
RuntimeError: failed to stop owned containers: ...
Error response from daemon: cannot remove container "pp_Xhyc_hot_gN":
  could not kill container: tried to kill container, but did not receive an exit event
```
It crashed three separate times, always at a switch point.

**Root cause.** `docker rm -f` intermittently returns non-zero with "did not
receive an exit event", but the container **does** die moments later (the env
self-heals to zero every time). The teardown code did one `docker rm -f` and
raised on any non-zero.

**Fix.** Make teardown idempotent + retrying:
```python
def stop_owned(names):
    running = [n for n in names if container_running(n)]
    if not running: return
    for _ in range(6):
        run_output(["docker", "rm", "-f", *running])
        time.sleep(2)
        running = [n for n in running if container_running(n)]
        if not running: return
    raise RuntimeError(f"failed to stop owned containers after retries: {running}")
```
Not OOM (200+ GiB free at crash, no dmesg OOM). Not SIGHUP — it still crashed
after switching to `nohup`, which is what proved the real cause was the docker hang.

## 2. A legitimately-failing ratio must not abort the run

**Symptom.** After 4h3c could not sustain even 4.0 QPS under SLO, the controller
exited with code 2 and the orchestrator (`subprocess.run(..., check=True)`)
treated it as fatal and died. On restart it would reload 4h3c, refail, exit-2,
crash again — an infinite crash loop. `best_ratio()` also did `float(None)` on
the failed ratio.

**Root cause.** `failed_low` (best_pass=None, one attempted probe) is a *valid
measurement* ("this ratio can't carry the floor"), not an orchestration error.

**Fix.**
- Treat controller exit-2 from `run-split`/`resume-split` as `skip_failed_low`,
  return cleanly, continue the sweep. Only truly-unexpected non-zero raises.
- `completed(section)` = best_pass is not None AND bracket has a numeric upper.
- `failed_low(section)` = best_pass is None AND fixed_qbase present AND probes
  present — skip it on restart (re-running just refails and reloads models).
- `best_ratio` selects only among `completed` ratios; returns "" if none, so the
  adaptive branch falls through instead of crashing.

## 3. kind GPU passthrough WITHOUT touching the host docker daemon

**Constraint.** The shared host has `docker info --format '{{.LiveRestoreEnabled}}'`
= **false**. Restarting dockerd (needed to change the default runtime) would
restart *all* neighbor containers. Editing the global
`accept-nvidia-visible-devices-as-volume-mounts` switch risks the neighbors too.
Both are forbidden.

**Fix — CDI route, node-local only.** See `scripts/setup-kind-gpu.sh`. Summary:
1. `nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml` (host; only *adds* a
   spec file, changes no existing behavior — zero neighbor risk).
2. Copy toolkit binaries (nvidia-ctk, nvidia-container-runtime,
   -runtime-hook, -container-cli) + `libnvidia-container.so.1` into the kind node.
3. Copy **all** driver libs/binaries the CDI spec lists under `hostPath:` into the
   node (51 files: libnvidia-ml, libcuda, nvidia-smi, ...), then `ldconfig`.
   The device-plugin needs NVML; the node has device nodes but no driver
   userspace until you do this.
4. `nvidia-ctk runtime configure --runtime=containerd --cdi.enabled` inside the
   node; restart **only the node's** containerd (`docker exec NODE systemctl
   restart containerd`) — never the host dockerd.
5. Create a `nvidia` RuntimeClass; run the NVIDIA k8s-device-plugin DaemonSet with
   `runtimeClassName: nvidia` (so the plugin container itself gets NVML).
6. Verify `kubectl get node -o jsonpath='{.status.allocatable.nvidia\.com/gpu}'`.

Pin a GPU pod to a specific card with `NVIDIA_VISIBLE_DEVICES=<UUID>`; note the
device-plugin assigns by its own index, so also verify from inside the pod which
physical card you actually got.

## 4. glibc vs musl — nvidia-smi "not found" in alpine

**Symptom.** In an alpine-based pod that has GPU devices + driver libs mounted,
`nvidia-smi` and CUDA still fail with `sh: nvidia-smi: not found` (exit 127) even
though `ls` shows the binary present.

**Root cause.** nvidia-smi/CUDA are compiled for glibc; alpine uses musl. The
dynamic loader can't run the ELF, and the shell reports "not found".

**Fix.** Use a glibc base image (debian/ubuntu, e.g. `python:3.11-slim`) for any
pod that must run GPU tooling. The vLLM image is already glibc.

## 5. ingress-nginx admission webhook race

**Symptom.** `kubectl apply -f ingress.yaml` fails with:
```
failed calling webhook "validate.nginx.ingress.kubernetes.io": ...
  dial tcp 10.x.x.x:443: connect: connection refused
```
right after installing ingress-nginx, even though the controller pod is Running.

**Fix.** Wait for the admission Service endpoint to be populated before applying
Ingress resources:
```bash
until kubectl -n ingress-nginx get endpoints ingress-nginx-controller-admission \
  -o jsonpath='{.subsets[0].addresses[0].ip}' | grep -q .; do sleep 5; done
```

## 6. kind is a separate containerd; images cost disk twice

**Symptom.** Deleting the old vLLM image on the host freed 0 bytes; `docker system
df` mislabels reclaimable space under the containerd image store.

**Root cause.** (a) docker here uses the containerd image store
(`io.containerd.snapshotter.v1`), so `docker rmi` of a tag whose layers are shared
frees nothing. (b) The kind node runs its *own* containerd and does not share the
host's images — `kind load docker-image` re-imports, and the peak disk cost is
roughly the uncompressed image size (a 48 GB vLLM image needs ~50 GB headroom).

**Fix.** Budget disk before importing. Monitor `df` during `kind load`. If the
node is rebuilt (e.g. to add `extraMounts`), the image and all GPU config are lost
and must be redone — which is exactly why `setup-kind-gpu.sh` is idempotent.

## 7. hostPath models need extraMounts at cluster-create time

**Symptom.** A vLLM pod with `hostPath: /home/<user>/hf` fails; the path doesn't
exist inside the kind node.

**Root cause.** kind nodes don't see host dirs unless declared. You cannot add a
mount to a running node — it requires recreating the cluster.

**Fix.** Put the weights dir in `kind-config.yaml` `extraMounts` (readOnly) before
`kind create cluster`. Recreating loses GPU setup, so re-run `setup-kind-gpu.sh`.

## 8. Cross-generation comparability

`num-gpu-blocks-override` differed between a 5-GPU run (capped at 6165) and a
7-GPU run (removed, vLLM auto-sizes KV under `--gpu-memory-utilization 0.94`).
That makes **absolute QPS non-comparable across generations** — only the *relative*
"split vs unified" trend is comparable. Always record: block override, mem-util,
PCIe link gen, offload cap, and per-hot-worker offload bytes (varies with hot
count). Report these in the comparability section.

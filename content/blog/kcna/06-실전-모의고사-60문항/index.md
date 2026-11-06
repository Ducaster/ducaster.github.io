---
title: '[KCNA] 실전 모의고사 60문항'
date: '2026-11-06T09:30:00+09:00'
categories:
- KCNA
tags:
- kubernetes
- kcna
- 모의문제
- 복습
- 시험 준비
series:
- KCNA
series_order: 14
---

개념 이름은 외웠는데, 같은 개념이 낯선 상황으로 나오면 답이 바로 골라지지 않았다. 그래서 KCNA 공개 출제 범위를 바탕으로 상황 문제 위주의 비공식 연습 문제 60문항을 새로 만들었다. 실제 시험과 같은 60문항, 90분 분량이다.

문제는 실제 시험처럼 영어로 쓰고, 풀이는 한국어로 달았다. 답은 모두 하나다. 해설 표에 영역을 같이 적어서 어느 도메인에서 틀렸는지 바로 보인다.

## 문제 구성

공식 출제 범위와 영역별 비중은 [Linux Foundation KCNA 안내](https://training.linuxfoundation.org/certification/kubernetes-cloud-native-associate/)와 [CNCF KCNA 안내](https://www.cncf.io/training/certification/kcna/)에서 확인할 수 있다. 표의 문항 수는 이 모의고사에서 배분한 값이다. 문제는 영역을 섞어서 냈다.

| 영역 | 공식 비중 | 문항 수 |
|---|---:|---:|
| 쿠버네티스 기초 | 44% | 26 |
| 컨테이너 오케스트레이션 | 28% | 17 |
| 애플리케이션 배포 | 16% | 10 |
| 클라우드 네이티브 아키텍처 | 12% | 7 |
| 합계 | 100% | 60 |

## 문제

**1.** After a scale request, a Deployment shows `spec.replicas: 5` and `status.readyReplicas: 3`. Which interpretation is correct?

- A. Three replicas are desired, and five have already been scheduled.
- B. Three replicas are desired until a rollout creates five new Pods.
- C. Five replicas are running, and three are receiving Service traffic.
- D. Five replicas are desired, and three are reported ready.

**2.** A node is healthy. Before tonight's maintenance, you need to stop ordinary newly scheduled Pods from landing there while leaving existing Pods in place for now. Which command fits?

- A. `kubectl cordon worker-3`
- B. `kubectl drain worker-3`
- C. `kubectl taint nodes worker-3 maintenance=true:NoExecute`
- D. `kubectl uncordon worker-3`

**3.** A Service has several backend Pods that change during rollouts. You want to see the actual backend IPs and readiness conditions that Kubernetes publishes for `checkout` in namespace `shop`. What should you inspect?

- A. The EndpointSlices in `shop` labeled `kubernetes.io/service-name=checkout`.
- B. The Service's DNS record for its ClusterIP.
- C. The Service's `spec.clusterIP` and `spec.ports`.
- D. The Deployment's `status.readyReplicas` and `status.availableReplicas`.

**4.** An old PVC was deleted. Its PV has reclaim policy `Retain` and now shows `Released`. A new PVC asks for the same class, access mode, and size. Why does Kubernetes not automatically hand it the released PV?

- A. A new claim can bind to that PV only if it requests more capacity than the old claim.
- B. `Released` means the provisioner is already deleting the backing disk.
- C. `Retain` keeps the old PVC object alive, so the new claim must wait for its deletion.
- D. The retained PV still holds the old claimant's data and needs manual reclamation before reuse.

**5.** A single CronJob starts a reconciliation task every ten minutes. The team wants to prevent two Jobs from this CronJob running concurrently without terminating a Job that is already running. Which setting fits?

- A. Set `successfulJobsHistoryLimit: 1`.
- B. Set `concurrencyPolicy: Replace`.
- C. Set `concurrencyPolicy: Allow` with one completion per Job.
- D. Set `concurrencyPolicy: Forbid`.

**6.** An engineer needs to open port 8080 of the running `billing-6d4b` Pod in a local browser for a short debug session. They must not create or change any Service or Ingress. Which command makes it available as `localhost:18080` on their workstation?

- A. `kubectl port-forward pod/billing-6d4b 8080:18080`
- B. `kubectl proxy --port=18080`
- C. `kubectl port-forward pod/billing-6d4b 18080:8080`
- D. `kubectl expose pod billing-6d4b --port=18080 --target-port=8080`

**7.** A Pod cannot start. Its events show that pulling an image from a private registry failed with `401 Unauthorized`. The registry credential Secret is valid and in the Pod's namespace, but no pull credentials are attached. Where should you reference it on the Pod?

- A. In the Pod's `serviceAccountName` field using the Secret name.
- B. In a Secret volume mounted in the application container.
- C. In the application container's `envFrom.secretRef`.
- D. In `spec.imagePullSecrets`.

**8.** From a debug Pod, `curl http://10.96.12.20/health` succeeds, but `nslookup catalog.shop.svc.cluster.local` times out. The Service's ClusterIP is `10.96.12.20`, and the cluster domain is `cluster.local`. What should you investigate first?

- A. The public DNS record for the application's Ingress.
- B. The application's container port and the Service's target port.
- C. The Pod's path to the cluster DNS resolver, including DNS egress and resolver health.
- D. The Service's selector and the readiness of its backend Pods.

**9.** A Pod has `nodeSelector: {disk: ssd}` and required node affinity for `zone=east`. All nodes have enough resources and no taints. Which node is eligible?

- A. A node labeled `disk=hdd` and `zone=east`.
- B. A node labeled `zone=east` with no `disk` label.
- C. A node labeled `disk=ssd` and `zone=east`.
- D. A node labeled `disk=ssd` and `zone=west`.

**10.** A metrics sidecar and the app share a Pod. The app listens only on `127.0.0.1:9100`. Which address lets the sidecar reach it?

- A. `127.0.0.1:9100`.
- B. The node IP on port `9100`.
- C. The Pod IP on port `9100`.
- D. A ClusterIP Service targeting port `9100`.

**11.** A pipeline publishes and retains one image per commit, then runs integration tests on it in staging. Production must not deploy the tested build if those tests fail. Which pipeline dependency enforces this?

- A. Require the staging tests to pass before production can deploy the tested build.
- B. Require the image build to pass, then run staging tests and production deployment in parallel.
- C. Require the image upload to pass, then run staging tests as an allowed-to-fail job.
- D. Require production deployment to pass before running the integration tests.

**12.** A platform team is comparing Kubernetes offerings from two vendors. It needs evidence that both implement the required Kubernetes APIs, while allowing differences in storage and load balancer integrations. What evidence is most relevant?

- A. Both offerings are Certified Kubernetes for the versions being evaluated.
- B. Both vendors package the same version of Helm.
- C. Both offerings list the same container runtime in their documentation.
- D. Both vendors are CNCF members.

**13.** A cluster has several add-ons installed. Which command lists the resource kinds this API server exposes and indicates which are namespaced?

- A. `kubectl config get-contexts`
- B. `kubectl get all -A`
- C. `kubectl api-resources`
- D. `kubectl api-versions`

**14.** The current context points to the correct cluster and defaults to `staging`. You want to list Pods in `payments` once without changing the context defaults. Which command does that?

- A. `kubectl get pods -n staging --field-selector metadata.name=payments`
- B. `kubectl get pods -n payments`
- C. `kubectl get pods --context=payments`
- D. `kubectl get pods --all-namespaces -l namespace=payments`

**15.** A Pod has an exporter and a viewer that share the same PVC-backed volume. The exporter must write reports, but the viewer's mount must be read-only. Which setting should change?

- A. Change the PVC's access mode to `ReadOnlyMany`.
- B. Set `readOnly: true` on the Pod's PVC volume source.
- C. Set `readOnlyRootFilesystem: true` on the viewer container.
- D. Set `readOnly: true` on the viewer container's `volumeMount`.

**16.** A container needs 70 seconds to load its cache on a cold start. `kubectl describe pod` shows `Liveness probe failed` followed by `Killing` at 30 seconds. After initialization, the team wants liveness checks to detect hangs quickly. Which change best meets both needs?

- A. A readiness probe with a failure window long enough for initialization.
- B. A longer liveness interval that also applies after initialization.
- C. An init container that waits for the app container's liveness endpoint.
- D. A startup probe that passes only after the cache is loaded and allows enough time for that to happen.

**17.** `kubectl describe node worker-2` shows `Ready: Unknown` with the reason `NodeStatusUnknown`. What does this tell the operator?

- A. The kubelet is reporting that the node is reachable but unhealthy.
- B. The control plane is no longer receiving timely heartbeats from that node.
- C. The node's running Pods have all failed their readiness probes.
- D. The scheduler has marked the node unschedulable for maintenance.

**18.** A Pod named `checkout-5f7b` has containers `app` and `proxy` in the current namespace. Both are running. Which command follows only the current `proxy` container's logs?

- A. `kubectl logs checkout-5f7b -c proxy --previous`
- B. `kubectl logs -f checkout-5f7b -c proxy`
- C. `kubectl logs -f checkout-5f7b --all-containers=true`
- D. `kubectl logs -f checkout-5f7b -c app`

**19.** A web app stores login sessions only in each replica's memory. Users are logged out when their replica is replaced during a rollout. What change makes sessions independent of replica lifetime?

- A. Enable Service session affinity so clients usually return to the same replica.
- B. Increase the number of replicas without changing where sessions are stored.
- C. Keep sessions in a shared external store that any replica can read.
- D. Increase the termination grace period so the old replica keeps its sessions longer.

**20.** A Helm chart exposes `replicaCount` and `resources` as values. The team wants to apply new production overrides stored in `prod-values.yaml` to an existing release, using the unmodified upstream chart. Which approach fits?

- A. Run `helm upgrade` with the chart and `-f prod-values.yaml`.
- B. Run `helm upgrade --reuse-values` without passing the production settings.
- C. Change `Chart.yaml` to describe the production settings before every upgrade.
- D. Patch the generated Deployment with `kubectl edit` after every Helm upgrade.

**21.** A Linux container repeatedly tries to use more than its configured CPU limit. Its memory use is within limits. How is the CPU limit normally enforced?

- A. The container is killed and restarted.
- B. The container is throttled.
- C. The container's CPU request is automatically raised.
- D. The Pod is evicted as soon as it crosses its CPU request.

**22.** A Pod's status reason is `Evicted`, and its message says the node was low on `ephemeral-storage`. The same node reports `DiskPressure=True`. Which explanation fits the evidence?

- A. The kernel killed the container for exceeding its memory limit.
- B. The Deployment scaled down and removed the Pod to match its replica count.
- C. The scheduler rejected the Pod before it could be assigned to a node.
- D. The kubelet evicted the Pod under node disk pressure.

**23.** The API accepts a custom `SearchCluster` object, but increasing its `spec.replicas` has no effect on actual search instances. What must exist to make that field drive the workload?

- A. A Service that selects the search Pods by label.
- B. A controller that watches the custom objects and reconciles search instances.
- C. A CRD schema that marks `spec.replicas` as required.
- D. An admission rule that checks `spec.replicas` is positive.

**24.** A team overwrites `shop:qa` in its registry. Two replacement Pods use that tag with `imagePullPolicy: IfNotPresent`; one node already has the old image for that tag and the other has never pulled it. Why can the replicas run different builds?

- A. The cached node can reuse its local image while the other node pulls the new one.
- B. The scheduler pins each replacement Pod to the build last run by its predecessor.
- C. Both nodes must resolve the tag remotely, but Deployment revision history selects one old build.
- D. The registry can update the tag only after all nodes evict their existing copies.

**25.** A Linux image defaults to UID 0 but supports running as UID 10001. A team wants the container to run as UID 10001 regardless of the image default. Which security setting selects that UID?

- A. `allowPrivilegeEscalation: false`.
- B. `runAsUser: 10001`.
- C. `fsGroup: 10001`.
- D. `runAsNonRoot: true`.

**26.** A container's entry script starts the server in the background and then exits. The container immediately terminates even though the server was launched. What change keeps the container tied to the server's lifetime?

- A. Expose the server port in the image so the runtime keeps the process alive.
- B. Set `restartPolicy: Always` so the background process outlives the script.
- C. Use a liveness probe to keep the container running after the script exits.
- D. Run the server in the foreground as the container's main process.

**27.** A developer wants to know whether their current identity is authorized to delete Deployments in `sandbox`, without attempting a deletion. Which command asks that question directly?

- A. `kubectl describe rolebindings -n sandbox`
- B. `kubectl auth can-i get deployments -n sandbox`
- C. `kubectl auth can-i delete deployments -n sandbox`
- D. `kubectl get deployments -n sandbox`

**28.** An engineer reproduces a bug in an upstream open source component and wants maintainers from multiple organizations to diagnose it. What should the engineer do first?

- A. Open separate reports in every downstream distribution that bundles the component.
- B. Search the upstream tracker and share versions and a minimal reproduction in the matching issue or a new report.
- C. Report it in the cloud provider's support portal and ask it to forward an internal ticket.
- D. Open a pull request with a local workaround and leave out the reproduction until someone requests it.

**29.** A PVC explicitly requests StorageClass `fast`. A static PV is Available with enough capacity and matching access and volume modes, but its class is `standard`. There is no dynamic provisioner or other PV. Why does the claim stay Pending?

- A. The available PV's storage class does not match the claim.
- B. The claim must request exactly the PV's capacity rather than less.
- C. The PV must enter `Bound` before it can be considered for a claim.
- D. The Pod must use the PV name instead of the PVC name in its volume spec.

**30.** A three-replica Deployment starts a RollingUpdate with all old replicas available and room for one extra Pod. Which settings target three available replicas throughout the rollout and cap the extra non-terminating replicas at one?

- A. `maxUnavailable: 0` and `maxSurge: 2`.
- B. `maxUnavailable: 0` and `maxSurge: 1`.
- C. `maxUnavailable: 1` and `maxSurge: 1`.
- D. `maxUnavailable: 1` and `maxSurge: 0`.

**31.** A build pipeline should attach a long build-report URL to a Deployment for humans and tools to read. No resource needs to select the Deployment using that value. Where should it go?

- A. In `spec.selector.matchLabels`.
- B. In `status.conditions`.
- C. In an annotation on the Deployment.
- D. In a label on the Deployment.

**32.** A PVC has a deletion timestamp and shows `Terminating` with the finalizer `kubernetes.io/pvc-protection`. A running Pod still references it. Which action addresses the expected blocker?

- A. Stop or update the workload so no Pod object still references the claim.
- B. Remove the volume mount from the container process while leaving the Pod spec unchanged.
- C. Delete the StorageClass that was used to provision the PV.
- D. Switch the PV reclaim policy from `Retain` to `Delete`.

**33.** Each of two otherwise eligible nodes has 600m of allocatable CPU left after existing requests. A single new Pod requests 1 CPU. With no preemption or scaling, what happens?

- A. The scheduler assigns it to one node and reserves the remaining 400m on the other.
- B. The scheduler places its containers across both nodes to satisfy the request.
- C. The Pod is scheduled because the cluster has 1200m free in total.
- D. The Pod remains unscheduled because neither node can fit it.

**34.** An Ingress object and its backend Service are accepted by the API. The Service works internally, and public DNS resolves to the intended entry point, but this cluster has no Ingress controller. What is missing?

- A. A NetworkPolicy that binds the Ingress hostname to the backend Pods.
- B. A CoreDNS rewrite that translates HTTP paths into Service names.
- C. An Ingress controller to implement the rules and program the traffic path.
- D. A `LoadBalancer` type on every backend Service so the API server can apply the Ingress.

**35.** An image has entrypoint `/bin/report` and default arguments `--format=text`. The Pod should keep `/bin/report` and replace the default argument with `--format=json`. Which override does that?

- A. Set `args: ["--format=text", "--format=json"]` and leave `command` unset.
- B. Set `command: ["/bin/report", "--format=json"]` and `args: ["--format=text"]`.
- C. Set `command: ["--format=json"]` and leave `args` unset.
- D. Set `args: ["--format=json"]` and leave `command` unset.

**36.** A node reports CPU `Capacity: 8` and `Allocatable: 7`. There are no other workload requests on it. Which figure does the scheduler use as the node's CPU budget for Pod requests?

- A. The sum of the CPU limits on the node.
- B. The current idle CPU shown by `kubectl top node`.
- C. `Allocatable: 7`.
- D. `Capacity: 8`.

**37.** A Deployment reads `LOG_LEVEL` from a ConfigMap using `env.valueFrom`. The ConfigMap changed, but the existing processes still report the old value. How can the team make the Deployment's Pods pick up the new value without rebuilding the image?

- A. Roll out replacement Pods that read the updated ConfigMap at startup.
- B. Wait for the kubelet to update the environment of the running processes.
- C. Add a checksum annotation only to the ConfigMap and leave the Pod template unchanged.
- D. Scale the Deployment up by one replica and leave all existing Pods in place.

**38.** An app writes an export to `/tmp/report.csv` in its container's writable filesystem, with no volume mounted there. The container is recreated in the same Pod. What should the team expect?

- A. The export persists because the replacement uses the same image digest.
- B. The export is restored from the node's image cache if the Pod stays on the same node.
- C. The replacement container starts with a fresh writable layer and does not retain the export.
- D. The export persists because the Pod's UID has not changed.

**39.** A retry-safe migration must reach one successful completion. If its worker Pod fails, Kubernetes should retry within a configured limit. Which workload fits?

- A. A Deployment with one replica.
- B. A CronJob with a daily schedule.
- C. A Job with one required completion.
- D. A StatefulSet with one replica.

**40.** A ClusterRole named `pod-reader` grants `get` and `list` on Pods. A RoleBinding in `dev` references it and names Maya as its subject. Assuming no other grants, where can Maya list Pods?

- A. Nowhere, because a RoleBinding can reference only a Role.
- B. In whichever namespace Maya sets as her kubeconfig default.
- C. In `dev` only.
- D. In all namespaces, because the referenced role is a ClusterRole.

**41.** A lab cluster has no implementation that provisions external load balancers. `kubectl get svc` shows a `LoadBalancer` Service with `EXTERNAL-IP <pending>`, while internal clients reach it successfully. What would allow Kubernetes to publish an external address for that Service type?

- A. Install or configure a load balancer implementation that supports the cluster.
- B. Add a public DNS record pointing to the Service's ClusterIP.
- C. Add an Ingress rule targeting the Service's ClusterIP.
- D. Open the Service port in the node firewall.

**42.** The analytics team prefers SSD nodes but wants new Pods to run on other eligible nodes whenever SSD nodes cannot fit them. Which setting expresses that preference?

- A. Preferred node affinity for `disk=ssd`.
- B. Required node affinity for `disk=ssd`.
- C. A toleration for an SSD-node taint, with no affinity rules.
- D. A `nodeSelector` for `disk=ssd`.

**43.** A team needs an approximate p95 request latency for a service across all its replicas using Prometheus. Which instrumentation lets it combine observations before calculating the percentile?

- A. Export a summary's p95 from each replica and average those p95 values.
- B. Export each replica's mean latency and weight it by its request count.
- C. Export the latest request duration as a gauge and take the maximum across replicas.
- D. Record latency in a histogram with the same bucket boundaries on each replica.

**44.** `kubectl describe pod checkout` shows `FailedCreatePodSandBox` and the message `plugin type="bridge" failed (add): no IP addresses available in range set`. Which subsystem should you investigate first?

- A. CoreDNS's upstream resolver configuration.
- B. The Pod network plugin and its IP address management configuration.
- C. The image registry's authentication and rate limits.
- D. The Service's ClusterIP allocator and its Service CIDR.

**45.** A container sets `limits.cpu: 600m` and omits `requests.cpu`. No admission mechanism supplies a CPU request. What CPU request is used for that container?

- A. `100m`, the standard fallback for an omitted CPU request.
- B. `600m`, copied from the limit.
- C. `0`, because the request was omitted.
- D. The node's current available CPU, up to `600m`.

**46.** An Argo CD application automatically syncs changed manifests. A managed ConfigMap was removed from Git while other desired resources remain. The ConfigMap stays in the cluster because the application does not automatically delete such resources. Which setting enables the intended cleanup on automated sync?

- A. Enable automated pruning for the application.
- B. Enable self-heal for the application.
- C. Increase the sync retry limit.
- D. Enable `allowEmpty` without enabling automated pruning.

**47.** A team is choosing an open source Layer 7 proxy to sit in the request path, route HTTP traffic, and collect upstream request statistics. Which project fits that role?

- A. OpenTelemetry Collector.
- B. Envoy.
- C. Prometheus.
- D. Fluentd.

**48.** A Kustomize base is shared by staging and production. Only production needs an extra environment variable on one Deployment. Where should the team put the change so staging is unaffected and both environments keep using the base?

- A. In a live edit to the production Deployment while leaving the production overlay unchanged.
- B. In the shared base Deployment manifest.
- C. In a new shared-base label indicating the production environment.
- D. In a Deployment patch referenced by the production overlay.

**49.** While writing a Deployment manifest, you want help on the API schema for `spec.strategy` without needing an existing Deployment. Which command should you use?

- A. `kubectl describe deployment checkout`
- B. `kubectl explain deployment.spec.strategy`
- C. `kubectl get deployment checkout -o yaml`
- D. `kubectl rollout history deployment/checkout`

**50.** A checkout team sets a target that at least 99% of valid requests finish successfully within 300 ms each week. Which measurement is the most direct service-level indicator for that target?

- A. The weekly fraction of valid requests that succeed within 300 ms.
- B. The weekly p99 latency calculated only for successful requests.
- C. The weekly fraction of time that average Pod CPU stays below 70%.
- D. The weekly fraction of valid requests that receive a successful response at any speed.

**51.** A Pod listens on TCP 8081. Its ClusterIP Service declares `port: 80` and `targetPort: 8080`; the EndpointSlice lists the expected Pod IP. Clients must keep using `http://catalog:80`. What should change?

- A. Set the Pod's declared `containerPort` to `8080` and leave the Service unchanged.
- B. Set the Service's `port` to `8081` and leave `targetPort` at `8080`.
- C. Set the Service's `targetPort` to `80` and leave `port` at `80`.
- D. Set the Service's `targetPort` to `8081` and leave `port` at `80`.

**52.** With NetworkPolicy enforcement enabled, both the client Pod's egress and the server Pod's ingress are isolated. A policy allows ingress to the server from the client, but no egress rule allows this flow from the client. What change is needed to let the connection start?

- A. Allow egress from the server to the client on the destination port.
- B. Add a second ingress policy on the server that allows the same client.
- C. Allow egress from the client to the server on the destination port.
- D. Allow ingress to the client from the server on the destination port.

**53.** Before applying a manifest, a pipeline needs the cluster's own validation and admission checks, including a dry-run-compatible policy webhook, without persisting the change. Which command fits?

- A. `kubectl apply --validate=strict -f app.yaml`
- B. `kubectl get -f app.yaml -o yaml`
- C. `kubectl apply --dry-run=server -f app.yaml`
- D. `kubectl apply --dry-run=client -f app.yaml`

**54.** The default scheduler is temporarily unavailable, but the API server and node components remain healthy. Which activity can still proceed for an already assigned Pod?

- A. The kubelet can restart one of its containers according to the Pod's restart policy.
- B. The API server can select a node for a newly created, unassigned Pod.
- C. The ReplicaSet can bind a replacement Pod directly to a healthy node.
- D. The kubelet can choose another node if its own node fills up.

**55.** A trace shows a slow request spanning `checkout` and `billing`. Both services emit structured logs with trace context. Which field should an engineer match to find logs from that same trace across the two services?

- A. The span ID of the root span.
- B. The trace ID.
- C. The service name.
- D. The Kubernetes Pod UID.

**56.** A team wants a workload to boot a different Linux kernel from the host. Which statement explains why a conventional Linux container alone cannot provide that?

- A. It selects its kernel from the base image, so it needs a different Linux distribution image.
- B. It shares the host kernel; a virtual machine can boot a guest kernel.
- C. It loads a private kernel only when the container runs in privileged mode.
- D. It shares the kernel with other containers only when they are in the same Pod.

**57.** A running Pod is healthy on `worker-a`. A new, mostly idle node joins. No descheduler or workload update is in play. What does the default scheduler do to that running Pod?

- A. It moves the Pod when the new node scores higher.
- B. It asks the ReplicaSet to replace the Pod on the new node.
- C. It removes the Pod's binding so the kubelet can choose again.
- D. It leaves the Pod on `worker-a`.

**58.** Two Pods are on the same node and reference the same bound PVC with `ReadWriteOnce`. Assume the volume driver supports sharing the mount on that node. What does this access mode allow?

- A. Only one container per node can mount it, regardless of how many Pods use the claim.
- B. Both Pods can mount the volume read-write on that one node.
- C. Only one Pod can mount it read-write, even when both Pods share a node.
- D. Both Pods can mount it read-write across different nodes in the same zone.

**59.** An engineer deletes one Pod owned by a Deployment's ReplicaSet and one standalone Pod with no controller. Both are gone from the API. Which Pod should be replaced automatically?

- A. Both Pods, provided the node that hosted them is healthy.
- B. Both Pods, provided their `restartPolicy` is `Always`.
- C. Only the ReplicaSet-owned Pod.
- D. Only the standalone Pod, because its kubelet still owns it.

**60.** A registry serves one tag for both `linux/amd64` and `linux/arm64` nodes. Which image artifact can reference a separate image manifest for each platform?

- A. An OCI image layer.
- B. An OCI image configuration for one platform.
- C. An OCI image manifest for one platform.
- D. An OCI image index.

## 답과 풀이

<details><summary>정답과 해설 펼치기</summary>

| 번호 | 답 | 영역 | 풀이 |
|---:|:---:|---|---|
| 1 | D | 쿠버네티스 기초 | `spec.replicas`는 목표 수이고 `status.readyReplicas`는 관측된 준비 수다. `spec.replicas: 5`만으로 다섯 개가 실행 중인지, Service가 어디로 요청을 보내는지 알 수 없다. |
| 2 | A | 쿠버네티스 기초 | `cordon`은 노드를 스케줄 불가로 표시하며 기존 파드를 내보내지 않는다. `drain`은 스케줄을 막는 데 더해 축출 대상 파드를 비운다. [노드 관리](https://kubernetes.io/docs/concepts/architecture/nodes/#manual-node-administration) |
| 3 | A | 컨테이너 오케스트레이션 | Service 이름으로 찾은 EndpointSlice에 백엔드 주소와 `ready` 조건이 있다. Deployment의 준비 복제본 수는 집계값이라 Service에 연결된 개별 주소와 상태를 보여 주지 않는다. [EndpointSlice](https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/) |
| 4 | D | 컨테이너 오케스트레이션 | `Retain`은 이전 PVC가 사라져도 저장소와 데이터를 남긴다. `Released`는 기존 클레임에서 풀린 상태이지 새 클레임에 바로 제공되는 `Available` 상태가 아니다. [Retain 정책](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#retain) |
| 5 | D | 쿠버네티스 기초 | `Forbid`는 같은 CronJob에서 이전 Job이 실행 중인 동안 새 Job을 동시에 시작하지 않는다. 조건에 따라 놓친 실행이 나중에 시작될 수 있다. `Replace`는 기존 실행을 중단하고 새 Job을 시작한다. [CronJob 정책](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#concurrency-policy) |
| 6 | C | 애플리케이션 배포 | `port-forward`는 `로컬:원격` 순서로 포트를 받으므로 로컬 18080을 파드 8080에 연결한다. 포트 순서를 바꾸면 로컬 8080에서 파드 18080으로 전달한다. [kubectl port-forward](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_port-forward/) |
| 7 | D | 컨테이너 오케스트레이션 | `imagePullSecrets`는 컨테이너가 시작되기 전에 레지스트리에서 이미지를 가져올 때 쓰는 자격 증명을 지정한다. `envFrom`으로 주입하는 환경 변수는 이미지를 가져오는 단계의 인증에 쓸 수 없다. [비공개 레지스트리 이미지](https://kubernetes.io/docs/tasks/configure-pod-container/pull-image-private-registry/) |
| 8 | C | 컨테이너 오케스트레이션 | ClusterIP로 앱에 도달하므로 백엔드 선택과 포트는 이 요청에서 동작했다. 이름 조회 자체가 시간 초과하므로 파드의 DNS 설정, DNS 서버까지의 연결과 DNS 서버 상태를 먼저 본다. [DNS 진단](https://kubernetes.io/docs/tasks/administer-cluster/dns-debugging-resolution/) |
| 9 | C | 쿠버네티스 기초 | `nodeSelector`와 필수 노드 어피니티를 함께 쓰면 두 조건을 모두 충족해야 한다. `zone=east`만 맞는 노드도 `disk=ssd`가 없으면 제외된다. [노드 선택 조건](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#node-affinity) |
| 10 | A | 쿠버네티스 기초 | 같은 파드의 컨테이너는 네트워크 네임스페이스를 공유해 루프백 주소로 통신할 수 있다. 앱이 루프백에만 바인딩돼 있으므로 파드 IP나 그 IP로 전달하는 Service로는 접근할 수 없다. [파드 네트워킹](https://kubernetes.io/docs/concepts/workloads/pods/#pod-networking) |
| 11 | A | 애플리케이션 배포 | 운영 배포가 같은 빌드의 테스트 성공에 의존해야 한다. 이미 저장소에 보관된 이미지에는 영향을 주지 않는다. 빌드 성공만 조건으로 두고 배포와 테스트를 병렬 실행하면 실패 결과가 나오기 전에 운영에 반영될 수 있다. |
| 12 | A | 클라우드 네이티브 아키텍처 | Certified Kubernetes는 해당 버전의 필수 Kubernetes API에 대한 적합성을 보여 주는 근거다. 같은 컨테이너 런타임을 써도 API 적합성이 입증되지는 않으며, 인증이 스토리지나 로드 밸런서 통합의 동일성을 뜻하지도 않는다. [CNCF 소프트웨어 적합성](https://www.cncf.io/training/certification/software-conformance/) |
| 13 | C | 쿠버네티스 기초 | `api-resources`는 서버가 제공하는 리소스 종류와 `NAMESPACED` 여부를 표시한다. `api-versions`는 API 그룹과 버전을 보여 주지만 리소스 종류별 범위를 표시하지 않는다. |
| 14 | B | 쿠버네티스 기초 | `-n payments`는 이번 요청의 네임스페이스만 지정한다. `--context=payments`는 네임스페이스 이름을 전달하는 옵션이 아니라 kubeconfig에서 `payments`라는 컨텍스트를 고른다. |
| 15 | D | 컨테이너 오케스트레이션 | 뷰어의 `volumeMount`에만 `readOnly`를 지정하면 같은 볼륨을 쓰는 내보내기 컨테이너의 마운트에는 적용되지 않는다. 파드의 PVC 볼륨 소스에 설정하면 그 볼륨의 모든 마운트가 읽기 전용으로 강제된다. [Pod API의 볼륨과 마운트](https://kubernetes.io/docs/reference/kubernetes-api/core/pod-v1/#PersistentVolumeClaimVolumeSource) |
| 16 | D | 애플리케이션 배포 | startup probe가 성공할 때까지 liveness probe는 시작되지 않으므로 초기화에 시간을 주고 이후에는 빠르게 장애를 감지할 수 있다. readiness probe가 실패해도 liveness 검사나 그에 따른 재시작을 막지 않는다. [Startup probe](https://kubernetes.io/docs/concepts/workloads/pods/probes/#startup-probe) |
| 17 | B | 쿠버네티스 기초 | `Ready: Unknown`은 노드의 하트비트가 제때 오지 않아 상태를 판단할 수 없다는 뜻이다. kubelet이 노드가 비정상이라고 보고하는 `Ready: False`와 다르며, 이 상태만으로 단절 원인은 확정할 수 없다. [노드 상태](https://kubernetes.io/docs/reference/node/node-status/#condition) |
| 18 | B | 애플리케이션 배포 | `-c proxy`가 컨테이너를 지정하고 `-f`는 새 로그를 계속 읽는다. `--previous`는 현재 실행 로그가 아니라 이전 컨테이너 인스턴스의 로그를 요청한다. [kubectl logs](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_logs/) |
| 19 | C | 클라우드 네이티브 아키텍처 | 공유 외부 저장소에 세션을 두면 교체된 복제본도 같은 데이터를 읽을 수 있다. 세션 어피니티는 가능한 동안 요청을 같은 백엔드로 보내지만, 그 백엔드가 종료되면 메모리 속 세션을 다른 복제본으로 옮겨 주지 않는다. |
| 20 | A | 애플리케이션 배포 | `helm upgrade -f`는 릴리스에 적용할 값 파일을 받아 기존 차트의 기본값을 덮어쓴다. 배포 후 `kubectl edit`로 수정하면 Helm 업그레이드에 쓰이는 값에 그 설정이 기록되지 않는다. [helm upgrade](https://helm.sh/docs/helm/helm_upgrade/) |
| 21 | B | 쿠버네티스 기초 | CPU 한도를 넘겨 쓰려 하면 CPU 시간이 제한된다. 한도를 넘겼다고 컨테이너를 종료하고 재시작하는 방식은 CPU 제한의 동작이 아니다. [리소스 한도](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/) |
| 22 | D | 컨테이너 오케스트레이션 | 노드의 임시 저장 공간 부족을 감지한 kubelet이 파드를 축출할 수 있다. 메모리 한도 초과로 컨테이너가 `OOMKilled`되는 경우와 달리, 여기서는 파드 상태와 노드 조건이 디스크 부족을 가리킨다. [노드 압박에 따른 축출](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/) |
| 23 | B | 쿠버네티스 기초 | 커스텀 컨트롤러가 `SearchCluster`의 목표 상태를 읽고 인스턴스를 조정해야 한다. CRD 스키마는 객체의 구조를 검증해도 필드가 지시하는 작업까지 실행하지 않는다. [Operator 패턴](https://kubernetes.io/docs/concepts/extend-kubernetes/operator/) |
| 24 | A | 쿠버네티스 기초 | `IfNotPresent`는 로컬에 해당 이미지가 있으면 재사용할 수 있다. Deployment의 리비전이 태그를 다이제스트로 고정해 주는 게 아니므로 같은 태그로 다른 빌드가 실행될 수 있다. [이미지 가져오기 정책](https://kubernetes.io/docs/concepts/containers/images/#image-pull-policy) |
| 25 | B | 컨테이너 오케스트레이션 | `runAsUser`가 프로세스의 UID를 지정한다. `runAsNonRoot`는 루트 실행을 막는 조건으로, 이미지가 기본으로 루트 사용자를 택할 때 대신 사용할 UID를 정해 주지는 않는다. [보안 컨텍스트](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/) |
| 26 | D | 쿠버네티스 기초 | 컨테이너 수명은 주 프로세스에 묶여 있으므로 서버를 포그라운드의 주 프로세스로 실행한다. `restartPolicy`는 종료 후 재시작 여부를 정할 뿐, 백그라운드 프로세스만 남은 컨테이너를 유지하지 않는다. [Dockerfile ENTRYPOINT](https://docs.docker.com/reference/dockerfile/#entrypoint) |
| 27 | C | 컨테이너 오케스트레이션 | `auth can-i`에 동사 `delete`, 리소스 `deployments`, 대상 네임스페이스를 주면 현재 권한을 확인할 수 있다. `get`이 허용돼도 `delete` 권한이 있다는 뜻은 아니다. [권한 확인](https://kubernetes.io/docs/reference/access-authn-authz/authorization/#checking-api-access) |
| 28 | B | 클라우드 네이티브 아키텍처 | 프로젝트 안내에 따라 중복을 확인하고 상위 프로젝트에 최소 재현 절차와 버전을 남기면 여러 조직의 유지보수자가 같은 곳에서 조사할 수 있다. 공급자 내부 티켓만으로는 상위 프로젝트에 재현 정보가 전달된다는 보장이 없다. [Kubernetes 이슈 분류 안내](https://www.kubernetes.dev/docs/guide/issue-triage/) |
| 29 | A | 컨테이너 오케스트레이션 | PVC가 `fast`를 요구하므로 `standard`인 PV는 용량과 접근 모드가 맞아도 바인딩되지 않는다. 용량은 요청값 이상이면 되므로 정확히 같을 필요는 없다. [PV와 PVC 바인딩](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#binding) |
| 30 | B | 애플리케이션 배포 | `maxUnavailable: 0`은 롤아웃 중 허용되는 가용 복제본 감소를 0으로, `maxSurge: 1`은 종료 중인 파드를 제외하고 목표보다 추가할 복제본의 상한을 1로 정한다. `maxUnavailable: 1`을 쓰면 추가 파드를 허용하더라도 가용 복제본이 둘까지 줄어들 수 있다. [Deployment RollingUpdate](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#rolling-update-deployment) |
| 31 | C | 쿠버네티스 기초 | annotation은 선택에 쓰지 않는 메타데이터를 담는다. label은 검색과 선택에 쓰이며 값의 길이와 문자에도 제약이 있어 긴 URL에 맞지 않는다. |
| 32 | A | 컨테이너 오케스트레이션 | PVC 보호는 참조 중인 파드 객체가 남아 있으면 삭제를 미룬다. 컨테이너 안에서 마운트를 해제해도 파드 명세의 참조는 남고, PV의 회수 정책 역시 이 보호 조건을 바꾸지 않는다. [사용 중인 스토리지 보호](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#storage-object-in-use-protection) |
| 33 | D | 쿠버네티스 기초 | 한 파드의 컨테이너는 한 노드에 배치되므로 어느 한 노드에 1000m가 남아 있어야 한다. 클러스터 전체의 여유를 합쳐도 이 파드를 수용할 수 없다. |
| 34 | C | 컨테이너 오케스트레이션 | Ingress는 라우팅 규칙을 선언하는 객체이고 이를 구현할 컨트롤러가 필요하다. 백엔드 Service의 유형을 바꿔도 호스트나 경로 규칙은 적용되지 않는다. [Ingress의 전제 조건](https://kubernetes.io/docs/concepts/services-networking/ingress/#prerequisites) |
| 35 | D | 쿠버네티스 기초 | `args`만 설정하면 이미지의 기본 실행 파일은 유지하고 기본 인자를 교체한다. `command`에 옵션 문자열만 넣으면 실행 파일 자체를 그 문자열로 바꾼다. [컨테이너 명령과 인자](https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/) |
| 36 | C | 쿠버네티스 기초 | 스케줄러는 파드에 할당 가능한 `Allocatable`을 예산으로 본다. `Capacity`는 노드의 전체 CPU 용량이라 시스템용으로 예약된 몫까지 포함할 수 있다. [노드 용량과 할당 가능량](https://kubernetes.io/docs/reference/node/node-status/#capacity) |
| 37 | A | 애플리케이션 배포 | ConfigMap에서 가져온 환경 변수는 실행 중인 프로세스에서 자동으로 갱신되지 않는다. 파일로 마운트한 경우의 갱신 동작과 다르므로, 이 Deployment에는 새 파드를 롤아웃한다. [ConfigMap 사용 방식](https://kubernetes.io/docs/concepts/configuration/configmap/#using-configmaps-as-files-from-a-pod) |
| 38 | C | 쿠버네티스 기초 | 새 컨테이너는 새 쓰기 계층을 사용한다. 파드 UID가 같아도 컨테이너의 파일이 파드 볼륨으로 옮겨지지는 않으므로 내보낸 파일은 보존되지 않는다. [볼륨과 컨테이너 파일시스템](https://kubernetes.io/docs/concepts/storage/volumes/) |
| 39 | C | 쿠버네티스 기초 | Job은 성공 횟수를 추적하고 실패 시 재시도할 수 있다. 한 번의 성공이 목표여도 실행 시도 자체가 딱 한 번이라고 보장하지는 않는다. 복제본이 하나인 Deployment는 작업의 완료를 기록하는 대신 실행 중인 복제본 수를 유지한다. |
| 40 | C | 컨테이너 오케스트레이션 | RoleBinding은 ClusterRole의 규칙을 참조할 수 있지만 네임스페이스 리소스에 대한 권한은 바인딩이 속한 `dev`에만 준다. ClusterRole을 참조했다는 이유로 클러스터 전체에 권한이 생기지는 않는다. [RBAC 바인딩](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#rolebinding-and-clusterrolebinding) |
| 41 | A | 컨테이너 오케스트레이션 | 외부 주소를 할당하려면 `LoadBalancer` Service를 처리하는 구현이 필요하다. 방화벽을 열면 이미 존재하는 경로의 접속은 허용할 수 있지만 외부 주소를 만들지는 않는다. [LoadBalancer Service](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer) |
| 42 | A | 쿠버네티스 기초 | 선호 노드 어피니티는 해당 노드에 가점을 주되 다른 적격 노드를 제외하지 않는다. 필수 어피니티나 `nodeSelector`는 SSD가 없는 노드를 후보에서 뺀다. |
| 43 | D | 클라우드 네이티브 아키텍처 | 같은 경계를 쓰는 히스토그램의 버킷별 관측 수를 합친 뒤 전체 p95를 추정할 수 있다. 복제본별 summary가 계산한 p95를 평균 내면 전체 요청의 p95가 되지 않는다. [Prometheus 히스토그램과 summary](https://prometheus.io/docs/practices/histograms/) |
| 44 | B | 컨테이너 오케스트레이션 | 파드 샌드박스에 주소를 할당하는 네트워크 플러그인의 `ADD` 단계에서 실패했다. Service CIDR은 Service 가상 IP의 주소 범위로 파드 주소 풀과 용도가 다르다. [클러스터 네트워킹](https://kubernetes.io/docs/concepts/cluster-administration/networking/) |
| 45 | B | 쿠버네티스 기초 | 다른 기본 요청값이 주어지지 않으면 Kubernetes는 CPU 한도 `600m`을 요청값으로 복사한다. 요청을 생략했어도 이 경우에는 0으로 계산하지 않는다. [요청과 한도](https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#requests-and-limits) |
| 46 | A | 애플리케이션 배포 | 자동 prune을 켜면 원하는 상태에서 빠진 관리 리소스를 동기화 때 삭제할 수 있다. self-heal은 라이브 상태의 변경으로 생긴 차이를 조정하는 옵션이고 삭제를 허용하는 prune 설정과는 별개다. [Argo CD 자동 prune](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/#automatic-pruning) |
| 47 | B | 클라우드 네이티브 아키텍처 | Envoy는 요청 경로에서 HTTP 라우팅과 요청 통계 수집을 할 수 있는 프록시다. OpenTelemetry Collector도 데이터를 받아 전달하지만 대상은 텔레메트리이며, 애플리케이션의 HTTP 요청 경로를 처리하는 프록시와는 역할이 다르다. [Envoy 소개](https://www.envoyproxy.io/docs/envoy/latest/intro/what_is_envoy) |
| 48 | D | 애플리케이션 배포 | 운영 오버레이에서 해당 Deployment에 패치를 적용하면 공통 베이스를 계속 쓸 수 있다. 베이스를 직접 수정하면 그 베이스를 참조하는 스테이징에도 변경이 들어간다. [Kustomize 베이스와 오버레이](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays) |
| 49 | B | 쿠버네티스 기초 | `kubectl explain`은 API 리소스의 필드 구조와 설명을 보여 준다. `describe`와 `get`은 이미 존재하는 객체의 상태나 설정을 확인할 때 쓴다. |
| 50 | A | 클라우드 네이티브 아키텍처 | 성공과 시간 제한을 모두 충족한 요청을 분자로, 전체 유효 요청을 분모로 삼으면 목표를 직접 측정할 수 있다. 성공한 요청만 골라 구한 p99는 실패한 요청을 집계에서 빼 버린다. [Google SRE의 SLI와 SLO](https://sre.google/sre-book/service-level-objectives/) |
| 51 | D | 컨테이너 오케스트레이션 | 클라이언트는 Service의 `port: 80`에 접속하고 Service는 `targetPort: 8081`로 전달해야 한다. `containerPort` 선언만 바꿔도 앱이 실제로 수신하는 포트는 바뀌지 않는다. [Service 포트](https://kubernetes.io/docs/concepts/services-networking/service/#field-spec-ports) |
| 52 | C | 컨테이너 오케스트레이션 | 연결을 시작하려면 보내는 쪽의 egress와 받는 쪽의 ingress가 모두 허용돼야 한다. 서버 쪽 ingress를 한 번 더 허용해도 클라이언트 쪽의 차단은 남는다. [NetworkPolicy 연결 규칙](https://kubernetes.io/docs/concepts/services-networking/network-policies/#the-two-sorts-of-pod-isolation) |
| 53 | C | 애플리케이션 배포 | 서버 dry-run은 실제 요청처럼 검증과 호환되는 admission 단계를 거치지만 변경을 저장하지 않는다. 클라이언트 dry-run은 API 서버의 admission을 실행하지 않으며 `--validate=strict`만 붙인 apply는 변경을 저장할 수 있다. [Kubernetes API dry-run](https://kubernetes.io/docs/reference/using-api/api-concepts/#dry-run) |
| 54 | A | 쿠버네티스 기초 | kubelet은 이미 자기 노드에 배정된 파드의 컨테이너를 관리한다. ReplicaSet은 대체 파드를 만들 수 있어도 그 파드를 노드에 배정하는 기본 스케줄러의 역할을 대신하지 않는다. [클러스터 구성 요소](https://kubernetes.io/docs/concepts/architecture/) |
| 55 | B | 클라우드 네이티브 아키텍처 | 트레이스 ID는 같은 트레이스 안의 서비스와 스팬을 가로질러 로그를 묶는 데 쓸 수 있다. 루트 스팬 ID는 특정 스팬만 식별하므로 하위 스팬에서 남긴 로그까지 찾을 수 없다. [OpenTelemetry 로그의 트레이스 문맥](https://opentelemetry.io/docs/specs/otel/logs/data-model/#trace-context-fields) |
| 56 | B | 쿠버네티스 기초 | 일반적인 리눅스 컨테이너는 호스트 커널을 공유한다. 다른 배포판 이미지는 사용자 공간을 바꿀 수 있지만 게스트 커널을 부팅하지는 않는다. [Docker의 컨테이너와 VM 설명](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/) |
| 57 | D | 쿠버네티스 기초 | 기본 스케줄러는 아직 노드에 배정되지 않은 파드를 배치한다. 새 노드의 점수가 높더라도 기존 파드를 옮기는 재균형 작업을 자동으로 수행하지 않는다. [스케줄러 동작](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/) |
| 58 | B | 컨테이너 오케스트레이션 | `ReadWriteOnce`는 읽기·쓰기 마운트가 가능한 노드를 하나로 제한한다. 파드 하나로 제한하는 모드는 `ReadWriteOncePod`이므로 같은 노드의 두 파드가 `ReadWriteOnce` 볼륨을 쓸 수 있다. [PV 접근 모드](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes) |
| 59 | C | 쿠버네티스 기초 | ReplicaSet은 목표 복제본 수를 맞추려고 새 파드를 만든다. `restartPolicy: Always`는 살아 있는 파드 안에서 컨테이너를 재시작하는 규칙이라 삭제된 독립 파드를 다시 만들지 않는다. |
| 60 | D | 쿠버네티스 기초 | OCI 이미지 인덱스는 플랫폼별 매니페스트를 가리킬 수 있다. 개별 이미지 매니페스트는 한 이미지의 설정과 레이어를 설명하며 여러 플랫폼 매니페스트를 묶는 역할은 인덱스가 한다. [OCI Image Index](https://specs.opencontainers.org/image-spec/image-index/) |

</details>

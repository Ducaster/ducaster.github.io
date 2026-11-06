---
title: '[KCSA] 실전 모의고사 60문항'
date: '2026-11-06T09:30:00+09:00'
categories:
- KCSA
tags:
- kubernetes
- kcsa
- security
- 모의문제
- 복습
- 시험 준비
series:
- KCSA
series_order: 10
---

설정 이름을 아는 것과 공격 경로에 맞는 통제를 고르는 것은 달랐다. 그래서 공개된 KCSA 출제 범위를 바탕으로, 사고 상황을 주고 통제를 고르는 비공식 연습 문제 60문항을 새로 만들었다. 실제 시험과 같은 60문항, 90분 분량이다.

문제는 실제 시험처럼 영어로 쓰고, 풀이는 한국어로 달았다. 답은 모두 하나다. 해설 표에 영역을 같이 적어서 어느 도메인에서 틀렸는지 바로 보인다.

공식 비중과 세부 항목은 [Linux Foundation 시험 안내](https://training.linuxfoundation.org/certification/kubernetes-and-cloud-native-security-associate-kcsa/)를 따른다. 표의 문항 수는 이 모의고사에서 배분한 값이다. 문제는 영역을 섞어서 냈다.

## 문제 구성

| 영역 | 공식 비중 | 이 글의 문항 수 |
|---|---:|---:|
| 보안 개요 | 14% | 8 |
| 구성 요소 보안 | 22% | 13 |
| 쿠버네티스 보안 기초 | 22% | 13 |
| 위협 모델 | 16% | 10 |
| 플랫폼 보안 | 16% | 10 |
| 컴플라이언스 | 10% | 6 |
| 합계 | 100% | 60 |

## 문제

**1.** A team already blocks risky Pod settings at admission. During an incident, investigators need to know which outbound destinations a compromised service actually contacted over the past hour, including successful connections. What should the team have collected and retained before the incident to answer that question?

- A. Store each admission decision together with the submitted Pod spec.
- B. Add a deny rule for the destination reported in the incident ticket.
- C. Collect network flow records with workload identity and retain them centrally.
- D. Record historical CPU and memory usage for the affected workload.

**2.** The API server uses the Node authorizer; a correctly identified kubelet for node-a attempts to read a Secret used by a Pod on node-b. The Secret has no direct or indirect relationship to any Pod on node-a. No other authorizer grants the request. What should the operator expect?

- A. The read is allowed because a valid node identity can read every Secret in the cluster.
- B. The read is allowed because the Secret and the requesting kubelet's Pods share a namespace.
- C. The read is denied until the Secret carries a label matching node-a.
- D. The read is denied because the Secret is unrelated to any Pod bound to node-a.

**3.** A Linux container writes temporary reports to `/scratch` and never needs to change files shipped with its image. Which setup lets report generation continue while preventing writes to the container root filesystem?

- A. Set `readOnlyRootFilesystem: true` and mount a ConfigMap at `/scratch`.
- B. Set `readOnlyRootFilesystem: true` and mount a writable `emptyDir` at `/scratch`.
- C. Keep the root filesystem writable and set `allowPrivilegeEscalation: false`.
- D. Keep the root filesystem writable and set `runAsNonRoot: true`.

**4.** A metrics sidecar listens on localhost inside a Pod. The network plugin enforces NetworkPolicy, but a newly added, less trusted container in the same Pod can still reach that listener. What change provides a boundary between them while still allowing authorized scrapers?

- A. Add an ingress rule that names the sidecar container as the destination.
- B. Disable shared process namespace for the Pod and keep the localhost listener.
- C. Move metrics to its own Pod and allow ingress only from approved scrapers.
- D. Bind the listener to the Pod IP and keep the same containers together.

**5.** An attacker can poison DNS for an internal API and owns a valid certificate for a different hostname from the same CA. The client must keep using DNS. Which client behavior prevents the impersonation?

- A. Validate both the certificate chain and the expected API hostname on every TLS connection.
- B. Reject DNS answers outside the private address range and accept any certificate from the CA.
- C. Require the latest supported TLS version but disable peer verification for internal traffic.
- D. Validate the chain against the internal CA but skip hostname verification for private addresses.

**6.** Under the NIST Secure Software Development Framework, a team fixes an authorization bypass that has appeared in three releases through the same shared helper. What best addresses the framework's goal of preventing similar vulnerabilities from recurring?

- A. Fix the shared helper's root cause and keep a regression test for the bypass.
- B. Require release signatures on the patched image and keep the development checks unchanged.
- C. Patch only the latest caller and close all related tickets after the next image scan.
- D. Add the incident to release notes and shorten the registry retention period.

**7.** An etcd snapshot is intact, but a recovery site cannot decrypt restored Secrets because they were written using KMS envelope encryption. Which recovery dependency must be included in the plan?

- A. Restore the etcd peer TLS CA and issue fresh peer certificates.
- B. Restore access to the original KMS keys and the matching API server provider configuration.
- C. Recreate the RoleBindings that let applications read their Secrets.
- D. Generate a replacement KMS key and point the restored API servers at that new key.

**8.** A controller knows the name of a precreated ConfigMap and must read that object without listing ConfigMaps or reading others in its namespace. Which RBAC rule meets the requirement?

- A. Grant `get` on all ConfigMaps in the namespace and configure the controller to use the expected name.
- B. Grant `list` on ConfigMaps with `resourceNames` and have the controller make an unfiltered list request.
- C. Grant `list` on ConfigMaps and have the controller filter the results locally.
- D. Grant `get` on ConfigMaps and put the single allowed name in `resourceNames`.

**9.** A reporting job requires a CSI volume that should be mounted by only one Pod cluster-wide, even when two Pods land on the same node. The driver supports both ReadWriteOnce and ReadWriteOncePod. Which change enforces that requirement?

- A. Use ReadWriteOnce and set the Deployment's replica count to one.
- B. Use ReadWriteOnce and spread the Pods across nodes with preferred anti-affinity.
- C. Use a claim with ReadWriteOncePod access mode for the reporting volume.
- D. Use ReadWriteMany and mark the application container's mount read-only.

**10.** An auditor sees a successful delete event for a Pod owned by a ReplicaSet. The event identifies the garbage collector as the caller. Assuming related API requests were logged, what should the auditor correlate to see whether a person initiated the cascade?

- A. Use the deleted Pod's application logs to identify the authenticated API caller.
- B. Correlate earlier deletes on the owner chain by object, time, and identity.
- C. Use the final Pod deletion event's audit ID to look up all prior requests in the cascade.
- D. Treat the garbage collector's recorded identity as proof that no user initiated the deletion.

**11.** A vulnerability in a base image library affects a running application even though its own source code is unchanged. The fix is already available in a newer base image. Which action removes the vulnerable library from the running service?

- A. Update the base image reference in source control and let existing Pods continue running.
- B. Block new deployments of the old image and leave existing replicas until their next scheduled release.
- C. Rebuild against the patched base, deploy the resulting image, and verify that old Pods are gone.
- D. Pull the patched base onto each node and restart containers using the existing application image digest.

**12.** The kubelet correctly identifies a monitoring client from its bearer token. The client should be able to read `/metrics` but must not execute commands in containers. Kubelet authorization is currently set to AlwaysAllow. What change meets both requirements?

- A. Switch kubelet authorization to Webhook and grant `get` on `nodes/metrics` only.
- B. Replace the bearer token with a client certificate and leave authorization unchanged.
- C. Shorten the token lifetime while leaving the kubelet's authorization mode unchanged.
- D. Disable anonymous authentication and keep kubelet authorization set to AlwaysAllow.

**13.** A container process is launched by exploiting an HTTP handler. No Kubernetes exec request appears in the API audit trail. Which evidence most directly distinguishes an application-spawned process from activity initiated through the Kubernetes API?

- A. Raise API audit logging to RequestResponse and inspect the application's parent process there.
- B. Compare the running container's image digest with the digest approved at deployment.
- C. Use Service request counts to infer whether a process was created.
- D. Correlate runtime process ancestry with API audit events for the affected container and time.

**14.** A platform rotates the CA for service TLS. Clients can trust two roots during the migration, and connections must keep working while servers move to certificates signed by the new CA. What sequence meets that constraint?

- A. Replace the clients' old root with the new root first, then rotate the servers one by one.
- B. Trust both roots first, rotate server certificates, verify, then drop the old root.
- C. Leave clients on the old trust root and rotate only the servers' leaf certificates to the new CA.
- D. Install the new serving certificates, distribute the new trust root afterward, and then remove the old root.

**15.** An ingress NetworkPolicy permits billing traffic from the frontend only. An older policy selecting the same billing Pods still allows every Pod in the namespace to reach the billing port. What change actually removes that extra access?

- A. Add an ingress policy with no allow rules that selects the same billing Pods.
- B. Remove or narrow the older allow rule, leaving the frontend allow rule in place.
- C. Add a default-deny ingress policy to the namespace that contains the frontend Pods.
- D. Recreate the frontend-only policy after the older policy so the newer policy takes precedence.

**16.** A team rolls back by image digest. Its registry garbage collection can delete untagged artifacts, and new nodes have empty image caches. What ensures rollback can pull the exact approved images during the retention window?

- A. Rely on images cached on the currently running nodes.
- B. Keep a movable `previous` tag without verifying what digest it points to.
- C. Retain approved rollback artifacts and test pulls by digest.
- D. Record the approved digests in Git and let the registry delete their untagged artifacts.

**17.** A node's host OS is confirmed compromised. The cluster has spare capacity and responders can isolate the node at the infrastructure layer without wiping it. What is the first containment step that blocks further network movement from the node while keeping its disk for investigation?

- A. Quarantine the node on the infrastructure network and preserve its disk.
- B. Apply egress restrictions to application Pods while leaving host connectivity unchanged.
- C. Drain the node to replace its workloads, leaving host networking available for the investigation.
- D. Cordon the node and wait for its existing Pods to finish.

**18.** Build jobs in two product lines use the same registry credential, so a leaked credential from the catalog pipeline can overwrite the payments image. Both pipelines still need to publish their own images. Which change best limits the blast radius of another leak?

- A. Give each pipeline its own credential with write access only to its repository.
- B. Rotate the shared write credential more often while keeping access to both repositories.
- C. Separate the images by tag prefix and keep the shared repository-wide write credential.
- D. Allow registry pushes only from the shared CI network.

**19.** A CIS benchmark report marks a control-plane file check as unavailable on a managed service because customers cannot access the host. The audit requires evidence for each applicable control. What should the team do?

- A. Rerun the same file check from a privileged customer worker and treat its result as control-plane evidence.
- B. Confirm applicability and ownership; obtain provider evidence or record the check as unresolved.
- C. Mark all control-plane checks as not applicable because one file is inaccessible.
- D. Mark the check as passed because the provider owns the control plane.

**20.** A cluster has a RuntimeClass named `sandboxed`, but its handler is installed on only one node pool. Pods must use that handler and must schedule only to nodes that support it. How should the operator configure placement?

- A. Set the RuntimeClass handler and give those Pods higher scheduling priority.
- B. Set the RuntimeClass handler and add a RuntimeClass scheduling node selector for the supporting pool.
- C. Label the supporting pool and use a selector while leaving the runtime handler at its default.
- D. Set the handler name and rely on the scheduler to infer support from the node's reported container runtime version.

**21.** A new advisory names a vulnerable package shipped in some application images. Assume the package has not changed at runtime. The deployed image tags have since been moved. Which observability data identifies running containers based on their actual platform images?

- A. Collect image pull success events grouped by namespace without recording artifact identity.
- B. Read image tags from the latest Deployment specs and scan each tag's current registry target.
- C. Match running containers' platform image digests to scan records for those digests.
- D. Read the registry's list of images with the vulnerable package and match them to application names.

**22.** A Pod needs to authenticate to an internal broker using Kubernetes identity. The broker checks the token audience, and the team wants a credential issued for that broker rather than one normally used for the Kubernetes API. What should it use?

- A. Copy a long-lived ServiceAccount token into a Secret for the broker client.
- B. Mount the cluster CA bundle and send the ServiceAccount name as a request header.
- C. Mount the default API token and make the broker accept the API server's audience.
- D. Mount a projected ServiceAccount token with the broker's audience and a bounded lifetime.

**23.** An operator enables API server encryption with an encrypting provider first and an identity fallback. Direct inspection still finds plaintext values in some Secret records created before the change. What migrates those live records?

- A. Rewrite the existing Secrets through the API, then verify the stored records.
- B. Read every Secret through the API to trigger encryption on access.
- C. Remove the identity fallback immediately and restart the API server.
- D. Rotate the API server's TLS serving certificate and take a new snapshot.

**24.** In a managed cluster, the contract assigns control-plane patching to the provider and worker image upgrades to the customer. The provider has patched the control plane, but a vulnerable kernel is still running on customer-managed workers. What closes the remaining exposure?

- A. Rebuild all application images with the latest base image and restart their Pods.
- B. Roll the workers onto a patched node image and verify their running kernel versions.
- C. Request a second control-plane patch and check the API server version.
- D. Apply a stricter seccomp profile and leave the worker image on its current version.

**25.** Under NIST CSF 2.0, a team has already contained a credential incident. It now restores a known-good service and checks data integrity before declaring the service operational. Which function best describes these current actions?

- A. Respond
- B. Protect
- C. Detect
- D. Recover

**26.** A regulated workload uses a required node selector. The cluster uses the Node authorizer and NodeRestriction, and a compromised general-purpose kubelet must not be able to make its node match the selector. Which design meets that condition?

- A. Use an ordinary custom label that kubelets are allowed to update, and require it in the Pod selector.
- B. Prefer approved nodes through soft node affinity and use anti-affinity to spread replicas.
- C. Require a NodeRestriction-protected label that only administrators can set.
- D. Give approved nodes a taint and add the matching toleration to the workload without a required selector.

**27.** Investigators delete a suspicious Pod and its owning Job, but the same payload returns every night. They confirm that a malicious CronJob owns the Jobs. What should they do to stop new scheduled runs and retain the configuration for investigation?

- A. Keep deleting the Pods as soon as a runtime alert fires and export each Pod's logs.
- B. Delete the current Job and extend Job history retention on the CronJob.
- C. Suspend the CronJob, keep its spec, and handle running Jobs separately.
- D. Scale the application's unrelated Deployment to zero and keep the CronJob enabled.

**28.** A namespace must reject new Linux Pods that add `NET_ADMIN`, while new replicas of legacy Pods that add only `NET_BIND_SERVICE` and run as UID 0 must still be admitted. Assume the legacy Pods otherwise meet Baseline. Which built-in Pod Security Admission setting meets both requirements?

- A. Enforce the Privileged profile and set Baseline in audit mode.
- B. Enforce the Baseline profile on the namespace.
- C. Set the Baseline profile only in warn mode.
- D. Enforce the Restricted profile on the namespace.

**29.** A PersistentVolume has reclaim policy Retain. Its claim was deleted after processing sensitive records, and the platform team wants to assign the storage to a new tenant. What must happen before reuse?

- A. Create a replacement claim in a different namespace and bind it to the retained volume.
- B. Delete the released PersistentVolume API object and recreate it for the new tenant.
- C. Change the StorageClass default reclaim policy before creating the new tenant's claim.
- D. Sanitize the backing storage and verify the old records are gone.

**30.** A compromised container is not in privileged mode, but it has unnecessary Linux capabilities and can make arbitrary outbound connections. Which pair of controls limits both paths after the image starts?

- A. Drop unnecessary capabilities and allow egress only to required destinations.
- B. Require an approved image signature and restrict pushes to the production registry.
- C. Run with a read-only root filesystem and enforce a memory limit.
- D. Encrypt node disks and require TLS to the registry.

**31.** A vendor sends a kubeconfig containing an `exec` credential plugin. An operator needs to inspect the target context without giving vendor-supplied code access to the workstation. What should the operator do first?

- A. Pin the cluster CA in the file before making the first API call.
- B. Use a short API request timeout when testing the supplied context.
- C. Use the file with a read-only Kubernetes identity and run a discovery command.
- D. Read it as text and obtain a trusted configuration for API calls.

**32.** A policy requires all production workloads to meet a baseline. A documented exception is approved for one namespace until a specific date. Which automation provides the clearest evidence that the exception did not silently become permanent?

- A. Track exception use by namespace and have the checker flag any use after the recorded expiry.
- B. Record the approval in a ticket and compare only monthly totals of passing workloads.
- C. Exclude the namespace from scanning until someone remembers to re-enable the rule.
- D. Keep scanning but suppress the rule's findings across the cluster while the exception is active.

**33.** A trusted mutating webhook injects a sidecar after a client submits a Pod. The registry policy must cover every image in the resulting Pod, including the injected image. Where should that check run?

- A. In a validating admission check against the final Pod after admission mutations.
- B. In a runtime alert that reports unapproved images after containers start.
- C. In a CI job that checks only the Pod manifest committed by the application team.
- D. In a mutating webhook that checks the incoming Pod before the injector runs.

**34.** A Deployment reads a database password from a Secret through an environment variable. The database accepts the old and new passwords during a short overlap, and the Secret has already been updated. What must happen before the old password is revoked?

- A. Set the Secret to immutable after the edit and wait for open sessions to reconnect.
- B. Roll the Pods so new containers start with the new value, then verify.
- C. Wait for kubelet's Secret cache to refresh and keep the existing processes running.
- D. Read the updated Secret through the API to trigger delivery into all existing processes.

**35.** A CI bearer credential was copied from a log and is being used outside CI. It has no other legitimate consumers, and responders can disable it immediately. Which action first stops replay without erasing the evidence already collected?

- A. Revoke the exposed credential at the issuer and preserve the log and audit records.
- B. Issue a replacement credential to CI and leave the original valid until its scheduled expiry.
- C. Delete the exposed line from the CI log and search for copies elsewhere.
- D. Block the source IP seen in the last request and keep the credential valid.

**36.** Production accepts only images signed by the release workflow. A test workflow signs another image using a signing certificate obtained through the same OIDC provider. What should admission verify before accepting the image?

- A. Verify the signature against the requested digest and accept any signer from the trusted identity provider.
- B. Match the repository name in the Pod spec to the release repository and require a signature to be present.
- C. Verify the digest's signature and require the release workflow's issuer and identity.
- D. Require a digest reference and check that the registry uses TLS.

**37.** A client Pod cannot open a new TCP connection to a server Pod. The server's ingress policy already allows the client, but the client's egress policy permits DNS traffic only. An enforcing CNI is in use. What is the narrowest policy change that enables the connection?

- A. Allow egress from the server Pods to the client Pods on ephemeral ports.
- B. Allow egress from the client Pods to the server Pods on the application port.
- C. Add a second ingress allow rule for the same client on the server.
- D. Allow ingress to the client Pods from the server Pods on the application port.

**38.** A public search endpoint builds SQL by joining user input into a query; all Pods already meet Restricted and the database accepts traffic only from the application. Which change closes the reported injection path?

- A. Require mutual TLS between the application and database.
- B. Limit the database role to reads against the search tables.
- C. Bind the search input as a query parameter.
- D. Move the database to a separate private subnet.

**39.** A user may update existing Pods' labels, but must never attach an ephemeral debug container. No other rules grant the user additional rights. Which RBAC design keeps the required update access while withholding debugger access?

- A. Grant patch and update on all Pod subresources, then omit create on `pods`.
- B. Grant patch on all resources in the core API group and restrict the rule to the user's namespace.
- C. Grant write access to `pods/ephemeralcontainers` but deny access to `pods/exec`.
- D. Grant the needed patch or update verbs on `pods` and omit them on `pods/ephemeralcontainers`.

**40.** A self-managed control plane trusts both a front-proxy client CA and a regular API client CA. A security review finds that the request-header CA trusts certificate holders outside the intended proxy. Which change best isolates the trust used for forwarded user identities?

- A. Use a request-header CA dedicated to the front proxy and set allowed proxy names.
- B. Rotate the API server's serving certificate and keep the existing request-header CA.
- C. Require TLS from the front proxy but accept identity headers from any certificate issued by either CA.
- D. Trust the regular API client CA for request headers and rely on each client's RBAC roles.

**41.** A support identity cannot use `pods/exec`, but it has `get` on `nodes/proxy` for routine troubleshooting. Its legitimate task needs only node inventory and health. Which change removes the unexpected command-execution path?

- A. Keep `get` on `nodes/proxy` but remove all write verbs on the proxy subresource.
- B. Limit direct network access to kubelets but keep API server proxy access for support.
- C. Keep proxy access and add an admission rule denying changes to Pod command fields.
- D. Remove `nodes/proxy` access and grant only the inventory and health reads the task needs.

**42.** A fail-closed validating webhook runs in its own namespace. It matches all Pod creates there, and after losing every replica it now blocks the Pods needed to restore itself. What design change avoids this dependency while keeping enforcement for tenant Pods?

- A. Set the webhook to Ignore for every namespace and alert when it becomes unavailable.
- B. Increase the webhook timeout without changing what requests it matches.
- C. Give the webhook's Pods a higher priority while keeping them subject to the same fail-closed check.
- D. Exclude the webhook's dedicated namespace from its match scope and tightly restrict who can deploy there.

**43.** A public service fetches customer-provided URLs. Its runtime identity can also reach an internal admin service that the fetch feature never needs. Which change most directly prevents an attacker from using that feature as a bridge to the admin service, even if URL validation misses a redirect?

- A. Check that the original URL begins with `https://` before following redirects.
- B. Require TLS with a valid server certificate on the admin service.
- C. Block fetcher-to-admin traffic while allowing the fetcher's required destinations.
- D. Add rate limits to the public fetch endpoint without changing what the fetcher can reach.

**44.** A service and its sidecar run in different containers, but one process can read the other's scratch files from a volume mounted into both. Neither process needs to share files. Which change most directly removes that access?

- A. Set different CPU limits for the two containers.
- B. Run the containers under different user IDs while keeping the scratch files world-readable.
- C. Mount a different scratch volume into each container.
- D. Mount the shared scratch volume read-only in the sidecar.

**45.** A new Pod in `production` cannot pull its private image. The nodes have no registry credentials, and the existing pull Secret is in `staging`. Both namespaces should retain separate credentials. How should production authenticate?

- A. Install a shared registry credential on every worker node.
- B. Create a production-scoped registry pull Secret in production and reference it from the Pod or its ServiceAccount.
- C. Reference the staging Secret by its namespace and name in the production Pod's imagePullSecrets.
- D. Grant the production ServiceAccount RBAC read access to the staging Secret and keep its current image pull configuration.

**46.** A ClusterRole already grants read access to Deployments. An operations group needs those permissions in `staging` only, and no other bindings apply. How should the role be assigned?

- A. Create a ClusterRoleBinding and set the group's kubeconfig context namespace to staging.
- B. Create a RoleBinding in the operations group's home namespace that references the existing ClusterRole.
- C. Create a RoleBinding in staging that references the existing ClusterRole.
- D. Create a ClusterRoleBinding to the existing ClusterRole and set its namespace to staging.

**47.** A workload no longer uses an old database password, but a readable backup bucket still contains exported Secret manifests with the password in the `data` field. The database still accepts it. What closes the exposed credential path and limits access to the remaining copies?

- A. Encrypt new backups and retain the existing bucket permissions until the next review.
- B. Remove the old Secret from the cluster and confirm that the new workload still works.
- C. Revoke the old password at the database and restrict and investigate access to the backup bucket.
- D. Enable encryption at rest on the cluster's API server and leave the backup bucket unchanged.

**48.** A security team wants to demonstrate detection coverage for the MITRE ATT&CK Deploy Container technique. The team's concern is attackers creating an unexpected workload through the Kubernetes API. Which evidence best demonstrates that specific coverage?

- A. Show an inventory of running workloads from before the simulation.
- B. Run a simulation that uses `kubectl exec` in an already running container and retain its alert.
- C. Show a passing benchmark check for the API server's TLS configuration.
- D. Create a test workload in an authorized simulation and retain its API event and alert.

**49.** A cluster's API is private. The platform permits outbound access to a trusted Git service but forbids external CI from opening inbound connections to the API. Which delivery design respects that boundary and still deploys approved changes?

- A. Expose the API through a public endpoint restricted to the CI provider's IP addresses.
- B. Use an in-cluster reconciler to pull approved changes from Git and apply them with scoped RBAC.
- C. Move the source repository into the private network but leave the external push runner as the only deployer.
- D. Give external CI a short-lived administrator token and keep the API unreachable from CI.

**50.** A self-managed cluster runs its built-in kube-controller-manager controllers under one broadly privileged identity. The operator wants API audit events to identify the individual controllers and wants each to use its own controller role. Which change addresses both goals?

- A. Enable per-controller service account credentials and use the corresponding controller RBAC bindings.
- B. Rotate the controller manager's shared client certificate for each release.
- C. Give the scheduler and controller manager separate shared identities while keeping all controllers on one identity.
- D. Keep the shared identity but split its permissions across several RoleBindings.

**51.** A release manager signs an image after receiving it from either of two builders. An incident review must establish which builder produced a particular digest and what build process it used. Which evidence meets that requirement?

- A. Check the registry push event for the account that uploaded the image.
- B. Verify the release manager's image signature and use the signing identity as the builder identity.
- C. Verify trusted provenance for the digest, including its builder identity and build definition.
- D. Compare the image's package list with the approved SBOM.

**52.** A CI system submits Pod templates and discards API warnings. Before enabling enforcement, the security team wants central audit evidence of templates that would violate Restricted without blocking the CI jobs. Which Pod Security Admission mode fits?

- A. Set audit to Baseline and let CI continue dropping response warnings.
- B. Set audit to Restricted and retain matching audit events.
- C. Set enforce to Restricted and record the requests that were rejected.
- D. Set warn to Restricted and retain the API server's audit events at Metadata.

**53.** A running Pod is sending customer data to an attacker over a TCP session. The incident team needs to stop the active transfer immediately and preserve the process for memory collection. The gateway can terminate live sessions; the CNI does not guarantee that policy updates will do so. Which action meets both needs?

- A. Terminate and block the exfiltration flow at the egress gateway; leave the Pod running.
- B. Apply a standard egress NetworkPolicy and assume it immediately closes the active session.
- C. Capture memory before taking any network action.
- D. Terminate the Pod and retain its exported logs and volume snapshot.

**54.** A Deployment's Pods currently mount the default ServiceAccount token, but the application does not call the Kubernetes API or any token-consuming service. The namespace default must remain unchanged for other workloads. What is the most targeted change?

- A. Set `automountServiceAccountToken: false` on the namespace's default ServiceAccount.
- B. Make the ServiceAccount token volume read-only and keep it mounted.
- C. Remove this ServiceAccount's RoleBindings but leave its token automount enabled.
- D. Set `automountServiceAccountToken: false` in this Deployment's Pod template.

**55.** A team removes a test backend from its Service and discovers that callers can still reach the backend's Pod IP. Production must keep its Service and limit new connections from non-host-network caller Pods to approved callers. No other policy grants broader ingress to the backend. Which control enforces that boundary?

- A. Apply an ingress NetworkPolicy to the backend Pods using an enforcing network plugin.
- B. Place the Service in a separate namespace while keeping the Pod network unchanged.
- C. Return the backend to its EndpointSlices and remove DNS access for unapproved callers.
- D. Keep the Service internal and restrict which namespaces may publish external Services.

**56.** In namespace `jobs`, an operator must change a Deployment's replica count by sending a PATCH to the scale endpoint without changing its image or Pod template. Assume the client is already allowed to read the Deployment. Which additional RBAC rule meets the requirement?

- A. Allow update on `deployments/status` in the apps API group in jobs.
- B. Grant patch on `deployments` in `jobs`, restricted to the named Deployment.
- C. Allow patch on `replicasets/scale` in the apps API group in jobs.
- D. Grant patch on `deployments/scale` in `apps`, scoped to `jobs`.

**57.** An Istio mesh enforces strict mutual TLS for the orders service. Every workload in the mesh has a valid identity, but only the checkout ServiceAccount should call orders. No existing authorization policy permits broader access. What additional control is required?

- A. Require the orders client to use the Service DNS name and leave peer permissions unchanged.
- B. Keep strict mutual TLS and trust any client with a certificate from the mesh CA.
- C. Apply an authorization policy that permits the whole namespace containing checkout.
- D. Add an authorization policy on orders that allows only checkout's ServiceAccount.

**58.** In a STRIDE review, a worker with legitimate queue access can change the amount in another tenant's job message; the threat statement focuses on the modification of data in transit between services. Which category best describes that outcome?

- A. Spoofing
- B. Information disclosure
- C. Elevation of privilege
- D. Tampering

**59.** A tenant can create large numbers of Jobs with tiny resource requests. The resulting objects overload the API server in a shared cluster before CPU or memory quotas are hit. Which control directly limits this path?

- A. Apply a LimitRange that sets a smaller default memory request for each container.
- B. Set a per-namespace ResourceQuota on the number of Job objects.
- C. Reduce completed Job retention without limiting the number of active Jobs.
- D. Lower the tenant's existing total CPU request quota.

**60.** Production uses Restricted Pod Security Admission, but application deployers can also patch the production Namespace object. Which change directly prevents them from weakening enforcement by relabeling that namespace while preserving workload deployment?

- A. Reserve Namespace updates for a separate role and keep deployers' workload permissions.
- B. Pin the Restricted enforcement version and keep deployers' current Namespace permissions.
- C. Set Restricted in warn mode as well and keep deployers' current Namespace permissions.
- D. Change deployers' Pod permissions from create to patch while leaving Namespace permissions intact.

## 답과 풀이

<details><summary>정답과 해설 펼치기</summary>

| 번호 | 답 | 영역 | 풀이 |
|---:|:---:|---|---|
| 1 | C | 보안 개요 | 사고 전에 워크로드와 연결된 흐름 기록을 남겨 두면 실제 통신의 목적지와 시각을 확인할 수 있다. 사고가 난 뒤 수집을 켜면 앞선 기록은 생기지 않는다. A의 어드미션 기록은 제출된 설정과 허용 여부를 보여 주지만 이후 통신을 기록하지 않는다. |
| 2 | D | 구성 요소 보안 | Node 인가의 Secret 접근은 해당 노드에 바인딩된 파드와의 참조 관계로 제한된다. B처럼 네임스페이스만 같아서는 그 관계가 성립하지 않는다. ([Node 인가](https://kubernetes.io/docs/reference/access-authn-authz/node/)) |
| 3 | B | 보안 개요 | 루트 파일 시스템은 읽기 전용으로 두고 `emptyDir`에만 임시 파일을 쓴다. D는 비루트 계정에 이미 쓰기 권한이 있는 이미지 경로를 읽기 전용으로 바꾸지 않는다. ([Security Context](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)) |
| 4 | C | 구성 요소 보안 | 같은 파드의 컨테이너는 루프백을 공유한다. 별도 파드의 IP에서 메트릭을 열고 승인된 수집기만 접근하게 한다. D는 주소만 바꿀 뿐 같은 파드 안의 접근을 차단하지 못한다. ([파드의 네트워크 공유](https://kubernetes.io/docs/concepts/workloads/pods/#pod-networking)) |
| 5 | A | 위협 모델 | 신뢰 체인과 예상 호스트 이름을 모두 확인하면 같은 CA가 서명해도 다른 이름의 인증서를 거부한다. D는 인증서를 발급한 CA만 확인하므로 공격자의 서버를 구별하지 못한다. ([RFC 9525: TLS 서비스 신원](https://www.rfc-editor.org/rfc/rfc9525.html)) |
| 6 | A | 컴플라이언스 | 공유 코드의 원인을 제거하고 우회 경로를 회귀 검사에 넣으면 같은 취약점이 다시 생기는지 확인할 수 있다. C는 한 호출부만 고쳐 다른 호출부와 공통 원인을 남긴다. ([NIST SSDF](https://csrc.nist.gov/pubs/sp/800/218/final)) |
| 7 | B | 구성 요소 보안 | 스냅샷 속 데이터 키를 풀려면 당시 키에 접근 가능한 KMS와 맞는 공급자 설정이 필요하다. D의 새 키로는 이전 키가 보호한 데이터 키를 복호화할 수 없다. ([KMS 봉투 암호화](https://kubernetes.io/docs/tasks/administer-cluster/kms-provider/)) |
| 8 | D | 쿠버네티스 보안 기초 | `get`과 `resourceNames`를 조합하면 지정한 객체만 직접 읽을 수 있다. A의 애플리케이션 설정은 정상 동작만 유도할 뿐 자격 증명을 탈취한 주체의 다른 객체 조회를 막지 못한다. ([RBAC 리소스와 이름](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#referring-to-resources)) |
| 9 | C | 구성 요소 보안 | ReadWriteOncePod는 지원하는 CSI 볼륨을 클러스터에서 한 파드만 사용하도록 제한한다. A의 ReadWriteOnce는 읽기·쓰기 마운트를 한 노드로 제한하므로 같은 노드의 여러 파드가 사용할 수 있고 복제본 수는 별도 파드의 사용을 막지 못한다. ([PV 접근 모드](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)) |
| 10 | B | 쿠버네티스 보안 기초 | 연쇄 삭제에서 파드 삭제의 직접 호출자는 컨트롤러일 수 있다. 상위 객체 삭제 기록을 연결해야 최초 요청을 찾을 수 있다. C의 audit ID는 API 요청 하나를 식별하므로 연쇄 요청 전체의 공통 ID가 아니다. ([감사 이벤트 API](https://kubernetes.io/docs/reference/config-api/apiserver-audit.v1/#audit-k8s-io-v1-Event)) |
| 11 | C | 보안 개요 | 새 베이스를 포함해 빌드한 이미지를 배포하고 이전 파드가 교체됐는지 확인해야 한다. D는 노드 캐시를 갱신해도 기존 앱 이미지의 레이어를 바꾸지 못한다. |
| 12 | A | 구성 요소 보안 | Webhook 인가는 SubjectAccessReview로 요청 권한을 확인한다. `/metrics`는 `nodes/metrics`로 확인하고, `nodes/proxy`를 빼야 명령 실행 경로를 열어 주지 않는다. D는 익명 요청을 막지만 이미 인증된 모니터링 클라이언트의 접근 범위를 줄이지 않는다. ([kubelet 인증·인가](https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/)) |
| 13 | D | 위협 모델 | 런타임의 부모 프로세스와 컨테이너 식별자를 API 감사 기록과 대조하면 실행 경로를 구분할 수 있다. A는 API 요청과 응답 본문을 더 기록해도 애플리케이션 프로세스의 계보를 남기지 않는다. |
| 14 | B | 플랫폼 보안 | 두 CA를 먼저 신뢰하면 교체 중인 서버와 아직 교체하지 않은 서버 모두에 연결할 수 있다. D는 클라이언트가 아직 새 CA를 신뢰하지 않는 동안 새 인증서를 내보내므로 검증이 실패할 수 있다. ([cert-manager 신뢰 번들 교체](https://cert-manager.io/docs/trust/trust-manager/#cert-manager-integration-intentionally-copying-ca-certificates)) |
| 15 | B | 쿠버네티스 보안 기초 | NetworkPolicy는 일치하는 허용 규칙을 합산하므로 기존의 넓은 허용을 없애거나 좁혀야 한다. A의 빈 수신 정책은 허용을 추가하지 않을 뿐 다른 정책의 허용을 덮어쓰지 않는다. ([NetworkPolicy 격리와 허용](https://kubernetes.io/docs/concepts/services-networking/network-policies/#the-two-sorts-of-pod-isolation)) |
| 16 | C | 플랫폼 보안 | 다이제스트는 내용을 지정하지만 저장소에서 그 내용을 보존하지는 않는다. D는 식별자만 남기므로 아티팩트가 삭제되면 새 노드가 가져올 수 없다. ([Harbor 가비지 컬렉션](https://goharbor.io/docs/main/administration/garbage-collection/)) |
| 17 | A | 위협 모델 | 인프라에서 노드의 네트워크 접근을 차단하면 호스트 수준의 이동을 막으면서 디스크를 보존할 수 있다. D의 cordon은 새 스케줄링을 막지만 기존 프로세스나 호스트의 통신은 끊지 않는다. |
| 18 | A | 보안 개요 | 저장소별 쓰기 권한을 주면 카탈로그 자격 증명으로 결제 이미지를 덮어쓸 수 없다. B는 자격 증명이 유효한 시간을 줄여도 유출 중 접근할 수 있는 범위는 그대로다. |
| 19 | B | 컴플라이언스 | 관리 책임과 적용 기준을 확인한 뒤 공급자 증빙을 확보하거나 미확인으로 남겨야 한다. D는 공급자 책임이라는 사실을 해당 통제가 충족됐다는 증거로 잘못 취급한다. ([CIS Kubernetes 벤치마크](https://www.cisecurity.org/benchmark/kubernetes)) |
| 20 | B | 구성 요소 보안 | RuntimeClass에 핸들러와 스케줄링 셀렉터를 함께 지정하면 런타임 선택과 노드 배치 조건이 모두 적용된다. D처럼 핸들러 이름만 주면 스케줄러가 노드별 핸들러 설치 여부를 알아내지 않는다. ([RuntimeClass 스케줄링](https://kubernetes.io/docs/concepts/containers/runtime-class/#scheduling)) |
| 21 | C | 플랫폼 보안 | 실행 중인 컨테이너가 받은 플랫폼별 이미지의 다이제스트를 그 이미지의 패키지 목록이나 스캔 결과와 연결하면 어떤 이미지에 취약한 패키지가 들어 있는지 알 수 있다. B는 이미 다른 이미지로 옮겨 간 태그를 조사할 수 있다. |
| 22 | D | 쿠버네티스 보안 기초 | 프로젝션으로 브로커를 대상으로 한 단기 토큰을 마운트한다. C는 브로커가 API용 토큰을 수락하도록 해 대상 서비스별 토큰 분리를 없앤다. ([ServiceAccount 토큰 설정](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#serviceaccount-token-volume-projection)) |
| 23 | A | 구성 요소 보안 | 저장 암호화는 쓰기 때 적용되므로 기존 Secret을 API로 다시 저장하고 확인한다. C는 평문을 암호화하지 않으며 마이그레이션 전에 빼면 해당 객체를 읽지 못할 수 있다. ([저장 암호화](https://kubernetes.io/docs/tasks/administer-cluster/encrypt-data/)) |
| 24 | B | 보안 개요 | 계약상 고객이 워커 이미지를 교체하고 실행 중인 커널 버전을 확인해야 한다. A는 컨테이너의 사용자 공간을 바꾸지만 워커 커널은 교체하지 않는다. |
| 25 | D | 컴플라이언스 | 복구본에서 서비스를 되살리고 데이터 무결성을 확인하는 활동은 Recover에 해당한다. A는 사고 관리와 완화에 초점을 두며 이 사례에서 이미 끝낸 격리가 그 예다. ([NIST CSF 2.0](https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf)) |
| 26 | C | 구성 요소 보안 | NodeRestriction이 보호하는 라벨 키를 필수 조건으로 쓰면 kubelet이 자기 노드를 승인 노드로 표시할 수 없다. A는 배치 조건이 엄격해도 kubelet이 라벨을 바꿀 수 있다. ([노드 격리 라벨](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#node-isolation-restriction)) |
| 27 | C | 위협 모델 | CronJob을 일시 중지하면 이후 예약 실행을 막으면서 설정을 보존할 수 있다. B는 현재 Job과 이력만 다루므로 다음 예약 실행은 계속된다. 이미 시작한 Job은 따로 조치해야 한다. ([CronJob 일시 중지](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/#schedule-suspension)) |
| 28 | B | 쿠버네티스 보안 기초 | Baseline은 `NET_ADMIN` 추가를 허용하지 않고 `NET_BIND_SERVICE`는 허용한다. C의 warn은 위반을 거절하지 않고, D의 Restricted는 UID 0인 레거시 파드까지 막는다. ([Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)) |
| 29 | D | 구성 요소 보안 | Retain은 PVC를 지워도 스토리지와 데이터를 남긴다. B처럼 PV 객체만 지워서는 실제 데이터가 삭제되지 않는다. ([PV 반환 정책](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaiming)) |
| 30 | A | 보안 개요 | 리눅스 capability를 줄이면 불필요한 커널 권한이 사라지고, 송신 허용 목록은 외부 연결을 제한한다. B는 배포 전 이미지 신뢰를 강화하지만 이미 실행 중인 이미지의 두 경로를 제한하지 않는다. |
| 31 | D | 구성 요소 보안 | kubeconfig의 `exec`는 클라이언트가 로컬 프로그램을 실행할 수 있게 한다. C의 읽기 전용 RBAC는 API 요청만 제한하므로 워크스테이션에서의 코드 실행을 막지 못한다. ([kubeconfig 주의 사항](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/)) |
| 32 | A | 컴플라이언스 | 범위와 만료를 기록하고 자동으로 계속 사용 여부를 확인하면 예외가 기한을 넘겼는지 추적할 수 있다. B의 승인 티켓과 전체 합계만으로는 어느 네임스페이스에서 예외가 지속되는지 알 수 없다. |
| 33 | A | 플랫폼 보안 | 검증 어드미션은 변경이 끝난 객체를 검사하므로 주입된 이미지까지 확인할 수 있다. D는 주입 전에 검사하므로 이후 추가된 이미지를 놓친다. ([변경 후 어드미션 검증](https://kubernetes.io/docs/reference/access-authn-authz/extensible-admission-controllers/)) |
| 34 | B | 쿠버네티스 보안 기초 | 환경 변수로 받은 Secret 값은 실행 중인 컨테이너에서 자동 갱신되지 않는다. C는 마운트된 Secret 파일의 갱신과 혼동한 경우다. ([Secret 사용](https://kubernetes.io/docs/concepts/configuration/secret/#using-secrets-as-environment-variables)) |
| 35 | A | 위협 모델 | 발급처에서 폐기하면 이미 복사된 자격 증명의 재사용을 멈추고 조사 기록은 남길 수 있다. B는 CI가 새 자격 증명을 쓰게 할 뿐 공격자가 가진 기존 자격 증명을 무효화하지 않는다. |
| 36 | C | 플랫폼 보안 | 검증이 이미지 다이제스트와 신뢰하는 서명 자격 증명을 연결해야 아티팩트 무결성과 서명자 신원을 확인할 수 있다. A는 같은 발급자의 테스트 워크플로까지 허용한다. ([Sigstore 서명 검증](https://docs.sigstore.dev/cosign/verifying/verify/)) |
| 37 | B | 쿠버네티스 보안 기초 | 연결을 시작하려면 출발지 송신과 목적지 수신이 모두 허용돼야 한다. C는 이미 허용된 수신만 바꾸므로 DNS만 허용하는 클라이언트 송신 정책이 계속 차단한다. |
| 38 | C | 보안 개요 | 매개변수 바인딩은 입력이 SQL 구문으로 실행되는 경로를 끊는다. B는 쓰기 피해를 줄여도 허용된 데이터의 유출까지 막지는 못한다. ([OWASP: SQL 주입 방지](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)) |
| 39 | D | 쿠버네티스 보안 기초 | 임시 컨테이너 추가는 `pods/ephemeralcontainers` 하위 리소스를 수정하는 별도 요청이다. A는 파드 생성 권한을 빼도 이미 존재하는 파드의 해당 하위 리소스 수정 권한을 남긴다. ([임시 컨테이너](https://kubernetes.io/docs/concepts/workloads/pods/ephemeral-containers/)) |
| 40 | A | 구성 요소 보안 | API 서버는 신뢰하는 프록시 인증서가 붙인 요청 헤더로 사용자 신원을 확인할 수 있다. 전용 CA와 허용 인증서 이름으로 프록시를 제한해야 한다. D는 일반 클라이언트의 신뢰와 전달 신원을 다루는 신뢰를 섞는다. ([프록시 CA 설정](https://kubernetes.io/docs/tasks/extend-kubernetes/configure-aggregation-layer/#ca-reusage-and-conflicts)) |
| 41 | D | 위협 모델 | `get`이라도 `nodes/proxy`는 kubelet API를 거쳐 컨테이너 명령 실행에 쓰일 수 있다. A처럼 쓰기 동사만 빼도 해당 실행 경로는 남는다. ([RBAC 권한 상승 위험](https://kubernetes.io/docs/concepts/security/rbac-good-practices/#access-to-proxy-subresource-of-nodes)) |
| 42 | D | 플랫폼 보안 | 관리 권한을 제한한 전용 네임스페이스를 검사에서 제외하면 웹훅이 없어도 복구용 파드를 만들 수 있다. A는 복구는 가능하게 하지만 장애 중 테넌트 파드도 검사 없이 통과시킨다. ([어드미션 웹훅의 자체 의존성](https://kubernetes.io/docs/concepts/cluster-administration/admission-webhooks-good-practices/)) |
| 43 | C | 위협 모델 | 네트워크 경로 자체를 막으면 리디렉션 검사가 빠져도 내부 관리 서비스에 닿지 않는다. A는 최초 URL의 스킴만 확인하므로 최종 목적지가 내부 서비스인지 막지 못한다. ([OWASP: SSRF 방지](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)) |
| 44 | C | 보안 개요 | 마운트를 분리하면 상대 컨테이너에 해당 파일 경로가 제공되지 않는다. D는 쓰기만 막고 파일 읽기는 허용한다. |
| 45 | B | 플랫폼 보안 | `imagePullSecrets`가 참조하는 Secret은 파드와 같은 네임스페이스에 있어야 한다. C처럼 다른 네임스페이스의 이름을 함께 적는 참조 방식은 지원하지 않는다. ([이미지 풀 자격 증명](https://kubernetes.io/docs/concepts/containers/images/#specifying-imagepullsecrets-on-a-pod)) |
| 46 | C | 쿠버네티스 보안 기초 | 네임스페이스의 RoleBinding이 ClusterRole을 참조하면 그 네임스페이스에만 권한을 부여한다. D의 ClusterRoleBinding은 클러스터 범위이며 네임스페이스로 범위를 좁힐 수 없다. |
| 47 | C | 위협 모델 | Secret의 `data` 값은 base64로 인코딩돼 복원할 수 있으므로 DB에서 폐기하고 백업 접근도 제한해야 한다. D는 클러스터의 저장 경로에 적용되며 이미 내보낸 파일이나 유출된 비밀번호를 보호하지 못한다. |
| 48 | D | 컴플라이언스 | 테스트 워크로드 생성과 그에 따른 감사 이벤트·경보를 연결하면 그 시험 시나리오에서 탐지가 작동했음을 확인할 수 있다. B는 기존 컨테이너에서 명령을 실행하는 별도 기법을 시험한다. ([MITRE ATT&CK T1610](https://attack.mitre.org/techniques/T1610/)) |
| 49 | B | 플랫폼 보안 | 클러스터 안의 조정기가 허용된 송신 경로로 변경을 가져와 제한된 권한으로 적용한다. A는 접근 IP를 좁혀도 금지된 외부 인바운드 경로를 만든다. ([Flux 조정 모델](https://fluxcd.io/flux/concepts/)) |
| 50 | A | 구성 요소 보안 | 컨트롤러별 ServiceAccount 자격 증명과 RBAC를 쓰면 각 컨트롤러에 별도 신원과 권한이 생긴다. D처럼 같은 주체에 바인딩을 나눠 붙이면 권한은 합산되고 감사 신원도 하나다. ([컨트롤러별 RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/#controller-roles)) |
| 51 | C | 플랫폼 보안 | 신뢰할 수 있는 빌드 출처 증명은 해당 다이제스트를 빌더와 빌드 방식에 연결한다. B는 이 사례에서 릴리스 서명자를 확인할 뿐 두 빌더 중 어느 쪽에서 만들었는지는 밝히지 못한다. ([SLSA 빌드 출처 증명](https://slsa.dev/spec/v1.2/build-provenance)) |
| 52 | B | 쿠버네티스 보안 기초 | Restricted의 audit 모드는 워크로드 템플릿 위반을 감사 이벤트에 표시하면서 요청을 허용한다. D의 warn은 클라이언트에 경고하며, 감사 수준을 설정해도 Restricted audit 모드의 위반 주석을 대신하지 못한다. ([Pod Security Admission](https://kubernetes.io/docs/concepts/security/pod-security-admission/#workload-resources-and-pod-templates)) |
| 53 | A | 위협 모델 | 기존 세션을 끊을 수 있는 지점에서 차단하면 유출을 멈추고 실행 중인 프로세스를 남길 수 있다. B는 문제의 CNI에서 이미 열린 연결을 즉시 끊는다고 보장할 수 없다. ([NetworkPolicy와 기존 연결](https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-s-impact-on-existing-connections)) |
| 54 | D | 쿠버네티스 보안 기초 | 파드 템플릿에서 자동 마운트를 끄면 이 워크로드에서만 기본 토큰을 빼게 된다. A는 같은 기본 ServiceAccount를 쓰는 다른 워크로드에도 영향을 준다. |
| 55 | A | 구성 요소 보안 | 수신 정책은 다른 일반 파드가 Service를 거쳐 접속하든 파드 IP로 직접 접속하든 백엔드 접근을 제한한다. C는 이름 조회만 막으므로 이미 아는 Pod IP에는 계속 접속할 수 있다. |
| 56 | D | 쿠버네티스 보안 기초 | `apps` API 그룹의 `deployments/scale`에 `patch` 권한을 주면 이 요청에 필요한 복제본 수 조정 경로만 열린다. B는 객체 이름만 제한하므로 그 Deployment의 이미지나 템플릿도 변경할 수 있다. |
| 57 | D | 플랫폼 보안 | 엄격한 mTLS는 호출자의 신원을 인증하고 전송을 보호한다. 호출 권한은 체크아웃 ServiceAccount로 좁혀야 한다. C는 같은 네임스페이스의 다른 신원도 허용한다. ([Istio 인가 정책](https://istio.io/latest/docs/reference/config/security/authorization-policy/)) |
| 58 | D | 컴플라이언스 | 이 위협 문장은 메시지 값의 무단 변경에 초점을 두므로 Tampering이다. C는 행위자가 더 높은 권한을 획득하는 데 초점을 두며, 이 사례에서는 기존 접근으로 데이터가 바뀌었다. ([Microsoft STRIDE 위협 분류](https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)) |
| 59 | B | 위협 모델 | `count/jobs.batch` 쿼터는 네임스페이스가 만들 수 있는 Job 객체 수를 직접 제한한다. C는 종료된 Job을 줄여도 동시에 생성하는 활성 Job 수를 제한하지 못한다. ([객체 수 쿼터](https://kubernetes.io/docs/concepts/policy/resource-quotas/#quota-on-object-count)) |
| 60 | A | 쿠버네티스 보안 기초 | Namespace 변경 권한을 분리하면 배포자가 강제 모드 라벨을 바꿀 수 없다. B의 버전 고정은 기준 버전만 정할 뿐 라벨 수정 권한을 없애지 않는다. |

</details>

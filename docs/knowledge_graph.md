# Codebase knowledge graph

This is a manually assembled, file-level map of the local workspace, based on
source imports and project documentation on 31 October 2026. Arrows describe the
labelled relationship; they do not imply a deployed service connection. It is
not a Graphify index and does not automatically update as files change.

## Key establishment and demos

```mermaid
flowchart TD
    demoE["scripts/demo_ecdh.py"] -->|uses| ecdh["src/classical_ecdh.py"]
    demoM["scripts/demo_mlkem.py"] -->|uses| mlkem["src/pqc_mlkem.py"]
    demoH["scripts/demo_hybrid.py"] -->|uses| integration["src/integration.py"]
    integration -->|verifies exchange| hybrid["src/hybrid_exchange.py"]
    hybrid -->|X25519 and HKDF| ecdh
    hybrid -->|encapsulation and decapsulation| mlkem
    ecdh -->|uses| crypto["cryptography library"]
    mlkem -->|uses| crypto
    hybrid -->|serialization and key types| crypto
    aead["src/hybrid_key_exchange.py"] -->|demonstrates with AES-GCM| hybrid
    testE["tests/test_ecdh.py"] -->|tests| ecdh
    testM["tests/test_mlkem.py"] -->|tests| mlkem
    testH["tests/test_hybrid.py"] -->|tests| hybrid
    testI["tests/test_integration.py"] -->|tests| integration
    testA["tests/test_hybrid_key_exchange.py"] -->|tests demo| aead
```

The hybrid exchange combines the X25519 and ML-KEM secrets using a
transcript-bound HKDF derivation. The integration interface reports public
metadata and validates agreement. This in-memory demonstration is
unauthenticated and is not a production TLS or mTLS implementation. See
[architecture](architecture.md) and [security limitations](security_limitations.md).

## Benchmarking and measurement

```mermaid
flowchart TD
    cli["scripts/benchmark.py"] -->|runs| bench["src/benchmark.py"]
    bench -->|measures| ecdh["src/classical_ecdh.py"]
    bench -->|measures| mlkem["src/pqc_mlkem.py"]
    bench -->|measures| hybrid["src/hybrid_exchange.py"]
    bench -->|writes samples and summaries| outputs["Benchmark artifacts"]
    plots["scripts/plot_benchmarks.py"] -->|reads summaries| outputs
    old["src/benchmark_hybrid.py"] -->|measures| ecdh
    old -->|measures| hybrid
    tls["scripts/benchmark_tls.py"] -->|measures connections| endpoint["TLS endpoint / OpenSSL"]
    verify["scripts/verify_tls_group.py"] -->|checks negotiated group| endpoint
    server["scripts/local_tls_server.py"] -->|provides local endpoint| endpoint
    tls -->|writes results| tlsout["TLS result files"]
    analysis["scripts/analyze_tls_results.py"] -->|reads and analyzes| tlsout
    bt["tests/test_benchmark.py"] -->|tests| bench
    tt["tests/test_benchmark_tls.py and tests/test_tls_benchmark.py"] -->|test| tls
    tt -->|test| verify
    tt -->|test| analysis
```

The in-process cryptographic benchmark and the TLS measurement are separate
experiments. The documented OpenSSL loopback study measures process-inclusive
duration, not isolated handshake latency. See the [current audit](project_audit_week2.md)
and [benchmarking guide](week2_benchmarking_guide.md).

## Policies, deployment examples, and documentation

```mermaid
flowchart LR
    policy["authz.rego"] -->|example policy input| input["input.json"]
    kp["kubernetes/network-policies/"] -->|contains| deny["default-deny ingress"]
    kp -->|contains| front["frontend to backend rule"]
    kp -->|contains| back["backend to database rule"]
    envoy["examples/envoy-tls-test/"] -->|contains| config["Envoy TLS example configuration"]
    readme["README.md"] -->|describes| arch["docs/architecture.md"]
    readme -->|points to| audit["docs/project_audit_week2.md"]
    app["app.py"] -->|imports| ui["Streamlit and pandas"]
```

The policy files and deployment configurations are examples or supporting
artifacts; their presence does not establish that the hybrid prototype is
integrated with or deployed to OPA, Envoy, or Kubernetes. Consult each file and
the project documentation for its current scope.

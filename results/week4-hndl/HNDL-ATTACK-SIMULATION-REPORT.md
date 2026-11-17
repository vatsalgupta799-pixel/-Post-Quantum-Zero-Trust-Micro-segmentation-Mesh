# Week 4 – Harvest Now, Decrypt Later (HNDL) Simulation

## 1. Objective

Demonstrate the Harvest Now, Decrypt Later (HNDL) threat by capturing and storing TLS 1.3 traffic using:
- Classical X25519 key exchange
- Hybrid X25519MLKEM768 key exchange

Compare the handshake evidence and explain the security implications.

## 2. Lab Environment

- Operating system: Kali Linux
- OpenSSL: 3.6.3
- TLS version: TLS 1.3
- Packet capture: tcpdump
- Packet inspection: tshark
- Network interface: loopback (lo)
- Server address: 127.0.0.1
- Server port: 8444
- Server certificate: project CA-issued certificate for CN=localhost

## 3. Classical X25519 Experiment

The TLS server was configured with the X25519 key-exchange group.

Client result:
- TLS version: TLS 1.3
- Cipher suite: TLS_AES_256_GCM_SHA384
- Negotiated group: X25519
- Connection: established
- Certificate verification: failed because the client was not configured to trust the project CA

Packet capture:
- File: classical-x25519.pcap
- Size: 3.6 KB
- Packets captured: 14
- Packets dropped by kernel: 0

Tshark confirmed:
- Client Hello supported group: x25519 (0x001d)
- Client key-share length: 32 bytes
- Server selected group: x25519

## 4. Hybrid X25519MLKEM768 Experiment

The TLS server was configured with the hybrid X25519MLKEM768 key-exchange group.

Client result:
- TLS version: TLS 1.3
- Cipher suite: TLS_AES_256_GCM_SHA384
- Negotiated group: X25519MLKEM768
- Connection: established
- Certificate verification: failed because the client was not configured to trust the project CA

Packet capture:
- File: hybrid-x25519-mlkem.pcap
- Size: 5.8 KB
- Packets captured: 14
- Packets dropped by kernel: 0

Tshark confirmed:
- Client Hello supported group: X25519MLKEM768 (0x11ec)
- Client key-share length: 1,216 bytes
- Server selected group: X25519MLKEM768
- Server key-share length: 1,120 bytes

## 5. Comparison

| Property | Classical | Hybrid |
|---|---|---|
| TLS version | TLS 1.3 | TLS 1.3 |
| Key exchange | X25519 | X25519 + ML-KEM-768 |
| Cipher suite | AES-256-GCM-SHA384 | AES-256-GCM-SHA384 |
| Client key share | 32 bytes | 1,216 bytes |
| Capture size | 3.6 KB | 5.8 KB |
| Packets captured | 14 | 14 |

The hybrid handshake contains larger key-share data because it includes ML-KEM material.

## 6. HNDL Security Analysis

HNDL describes an attacker collecting encrypted data today and retaining it for possible decryption in the future.

A sufficiently capable fault-tolerant quantum computer running Shor's algorithm could threaten classical elliptic-curve key exchange such as X25519. This creates a risk for recorded sessions if their confidentiality depends on that classical key exchange.

ML-KEM is designed to provide post-quantum key establishment. The hybrid X25519MLKEM768 group combines classical and post-quantum key establishment, providing an additional post-quantum security component.

The experiment demonstrates traffic capture and handshake comparison. It does not perform quantum computation or decrypt either capture.

## 7. Limitations

- Both experiments used loopback traffic on one machine, not a real enterprise network.
- No quantum computer or quantum decryption attack was performed.
- The certificate verification warning appeared in both client tests because the project CA was not supplied as a trusted CA to the client.
- The certificate uses an RSA signature. The experiment compares key exchange groups, not post-quantum certificate authentication.
- PCAP file size is not a direct measure of cryptographic security.
- The experiment does not establish that hybrid TLS is immune to every possible attack.

## 8. Conclusion

The experiment successfully captured and inspected TLS 1.3 traffic using classical X25519 and hybrid X25519MLKEM768 key exchange.

The packet captures provide evidence of the negotiated groups and the larger hybrid key shares. The results illustrate why organizations should consider post-quantum key establishment to reduce future HNDL exposure.

## 9. Evidence Files

- results/week4-hndl/classical-x25519.pcap
- results/week4-hndl/hybrid-x25519-mlkem.pcap

## 10. Supporting Performance Benchmark (Earlier Week 2 Test)

An earlier paired benchmark compared classical X25519 and hybrid X25519MLKEM768 using TLS 1.3.

Test configuration:
- 100 measured attempts per configuration
- 10 warm-up attempts
- OpenSSL client and server
- Loopback interface (127.0.0.1)
- TLS 1.3

| Metric | Classical X25519 | Hybrid X25519MLKEM768 |
|---|---:|---:|
| Successful attempts | 100/100 | 100/100 |
| Mean duration | 1037.43 ms | 1035.69 ms |
| P50 duration | 1035.62 ms | 1035.10 ms |
| P95 duration | 1050.70 ms | 1039.87 ms |
| P99 duration | 1055.29 ms | 1043.56 ms |

These measurements include process startup, TCP connection, TLS handshake, certificate verification, output capture, and process exit. They are not isolated TLS handshake timings.

The results are from an earlier experiment and are supporting performance evidence, not measurements from the Week 4 packet-capture experiment.


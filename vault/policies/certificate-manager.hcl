path "pki/sign/service-a-role" {
  capabilities = ["update"]
}
path "pki/cert/ca" {
  capabilities = ["read"]
}
path "sys/capabilities-self" {
  capabilities = ["update"]
}

resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
  }
}

resource "helm_release" "argocd" {
  name       = "argocd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name

  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"

  depends_on = [
    kubernetes_namespace.argocd
  ]
}
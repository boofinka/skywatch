resource "kubernetes_manifest" "skywatch_application" {
  manifest = {
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"

    metadata = {
      name      = "skywatch"
      namespace = "argocd"
    }

    spec = {
      project = "default"

      source = {
        repoURL        = "https://github.com/boofinka/skywatch.git"
        targetRevision = "main"
        path           = "helm/skywatch"
      }

      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "default"
      }

      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
      }
    }
  }

  depends_on = [
    helm_release.argocd
  ]
}
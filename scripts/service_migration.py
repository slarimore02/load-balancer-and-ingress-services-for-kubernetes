import copy
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
import argparse
import os.path
from pprint import pprint

IP_ANNOTATION = 'load-balancer-ips'
def update_annot(v1, svc):    
    '''
    ************************************************************************
    Take dictionary of original service, copies Service.status.load_balancer.ingress[0].ip to Service.metadata.annotations and patches Service
    --------------
    Arguments:
    v1 :: CoreV1Api object
    svc :: original service as dictionary
    --------------
    Returns:
    None
    ************************************************************************
    '''
    
    svc['metadata']['annotations'][IP_ANNOTATION] = svc['status']['load_balancer']['ingress'][0]['ip']
    service = client.V1Service()
    service.api_version = "v1"
    service.kind = "Service"
    service.metadata = svc['metadata']
    service.spec = svc['spec']
    service.status = svc['status']
    try:
        api_response = v1.patch_namespaced_service(name = svc["metadata"]["name"], namespace="avi-system", body=service)
        #updated_service = v1.read_namespaced_service(name = svc["metadata"]["name"], namespace="avi-system")
    except ApiException as e:
        print(e)

def get_svc(config_file):
    '''
    ************************************************************************
    Takes a kubeconfig file and retrieves all services found in all namespaces. If service if of type LoadBalancer, then calls update_annot() to patch service
    --------------
    Arguements:
    config_file :: kubeconfig file path
    --------------
    Returns:
    svc_dict :: Dictionary storing values of all services as 
    {<SERVICE_NAME>:{
                    <SERVICE_NAME>, 
                    <SERVICE_NAMESPACE>, 
                    <SERVICE_CLUSTER_IP>, 
                    <SERVICE_TYPE>, 
                    <SERVICE_VS_IP> (if SERVICE_TYPE==LoadBalancer)
                    }
    }
    ************************************************************************
    '''
    config.load_kube_config(config_file=config_file)
    v1 = client.CoreV1Api()
    ret = v1.list_service_for_all_namespaces()
    svc_dict = {}
    updated_svc = []
    not_updated_svc = []
    for svc in ret.items:
        svc_dict[svc.metadata.name] = {'name':svc.metadata.name, 'namespace':svc.metadata.namespace, 'cluster_ip':svc.spec.cluster_ip, 'type':svc.spec.type}
        if svc.spec.type == 'LoadBalancer':
            if 'load-balancer-ips' not in svc.metadata.annotations:
                updated_svc.append(svc.metadata.name)
                new_lb = copy.deepcopy(svc.to_dict())
                update_annot(v1, new_lb)
            else:
                not_updated_svc.append(svc.metadata.name)
    print("Services updated: ", updated_svc)
    print("Services not updated: ", not_updated_svc)
    return svc_dict

def main():
    parser = argparse.ArgumentParser(description="Script to read all namespaced services and add external IP to service annotation for LoadBalancer type services")
    parser.add_argument('kubeconfig_file', help="Path of kubeconfig file in local directory")
    args = parser.parse_args()
    config_file = args.kubeconfig_file
    while not os.path.isfile(config_file):
        config_file = input("Give valid kubeconfig filepath (Input \'End\' to exit program): ")
        if config_file == 'End' or config_file=='end':
            break
    if os.path.isfile(config_file):
        services = get_svc(config_file)
        pprint(services)
    
if __name__ == '__main__':
    main()
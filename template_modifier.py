import json
import requests
import openstack_controller as oc
# 램, 디스크, 이미지, 네트워크 이름, 키페어 네임,
def getUserRequirement(param_needs, param_os, param_package, param_num_people, param_data_size, param_instance_name, param_backup_time, request):
    token = request.headers["X-Auth-Token"]
    user_needs = param_needs
    user_os = param_os
    user_package = param_package
    disk_size = param_num_people * param_data_size
    flavor_payload = {
        "flavor": {
            "name": "test_flavor",
            "ram": 1024,
            "vcpus": 2,
            "disk": disk_size,
            "id": "10",
            "rxtx_factor": 2.0,
            "description": "test description"
        }
    }

    flavor_make_req = requests.post("http://" + oc.hostIP + "/compute/v2.1/flavors/",
            headers = {'X-Auth-Token' : token},
            data = json.dumps(flavor_payload))
    flavor = flavor_make_req.json()["flavor"]["name"]
    
    # if disk_size < 20:
    #     flavor = "m1.small"
    # elif 20 <= disk_size < 40:
    #     flavor = "m1.medium"
    # else :
    #     flavor = "m1.large"

    user_instance_name = param_instance_name
    backup_time = param_backup_time

    return user_needs, user_os, user_package, flavor, user_instance_name, backup_time


def templateImageModify(template, user_id, user_instance_name, flavor, user_package, instance_num):
    with open(template, 'r') as f:
        template_data = json.load(f)
    template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
    template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name) # 인스턴스 name 설정
    template_data["template"]["resources"]["mybox"]["properties"]["flavor"] = flavor    # flavor 설정
    template_data["template"]["resources"]["myconfig"]["properties"]["cloud_config"]["packages"] = user_package    # package 설정
    template_data["template"]["resources"]["demo_key"]["properties"]["name"] = user_id + str(instance_num)  # 키페어 name 설정
    template_data["template"]["resources"]["mynet"]["properties"]["name"] = user_id + "-net" + str(instance_num)    # 네트워크 name 설정
    template_data["template"]["resources"]["mysub_net"]["properties"]["name"] = user_id + "-subnet" + str(instance_num) # sub네트워크 name 설정
    template_data["template"]["resources"]["mysecurity_group"]["properties"]["name"] = user_id + "-security_group" + str(instance_num) # 보안그룹 name 설정
    print(json.dumps(template_data))

    # return(template_data)

def templateFlavorModify(template, user_stack_num):
    with open(template, 'r') as f:
        template_data = json.load(f)
    
    template_data["stack_name"] = template_data["stack_name"] + str(user_stack_num)
    print(json.dumps(template_data))

# def templateImageModify(template):
#     with open(template, 'r') as f:
#         template_data = json.load(f)
#     print(json.dumps(template_data))

templateImageModify("templates/cirros.json", "user1", "instance_1", "m1.nano", ["https", "apache2"], 2)
#templateFlavorModify("templates/cirros.json", 3)
import json
import requests
import openstack_controller as oc
# 램, 디스크, 이미지, 네트워크 이름, 키페어 네임,
def getUserRequirement(input_data, user_id, instance_num, token):
    user_token = token
    admin_token = oc.admin_token()
    #input_data = json.loads(request.body)
    #user_needs = input_data["needs"]#param_needs
    user_os = input_data["os"]#param_os
    user_package = input_data["package"]#param_package
    disk_size = round(input_data["num_people"] * input_data["data_size"])#param_num_people * param_data_size
    
    if disk_size < 5:
        flavor = "ds512M"#flavor_make_req.json()["flavor"]["name"]
    elif 5 <= disk_size <= 10:
        flavor = "m1.tiny"  # test한다고 tiny 준거임.
    # elif 10 <= disk_size <= 20:
    #     flavor = "ds4G"
    elif 10 < disk_size :
        flavor = "EXCEEDED"
    
    # if disk_size < 20:
    #     flavor = "m1.small"
    # elif 20 <= disk_size < 40:
    #     flavor = "m1.medium"
    # else :
    #     flavor = "m1.large"

    user_instance_name = input_data["instance_name"]#param_instance_name
    backup_time = input_data["backup_time"]#param_backup_time

    return user_os, user_package, flavor, user_instance_name, backup_time #user_needs, 


def templateModify(template, user_id, user_instance_name, flavor, user_package, instance_num):
    # with open(template, 'r') as f:
    #     template_data = json.load(f)
    template_data = template
    template_data["stack_name"] = str(user_instance_name)   # 스택 name 설정
    template_data["template"]["resources"]["mybox"]["properties"]["name"] = str(user_instance_name) # 인스턴스 name 설정
    template_data["template"]["resources"]["mybox"]["properties"]["flavor"] = flavor    # flavor 설정
    template_data["template"]["resources"]["myconfig"]["properties"]["cloud_config"]["packages"] = user_package    # package 설정
    template_data["template"]["resources"]["demo_key"]["properties"]["name"] = user_id + "_" + str(instance_num)  # 키페어 name 설정
    template_data["template"]["resources"]["mynet"]["properties"]["name"] = user_id + "-net" + str(instance_num)    # 네트워크 name 설정
    template_data["template"]["resources"]["mysub_net"]["properties"]["name"] = user_id + "-subnet" + str(instance_num) # sub네트워크 name 설정
    template_data["template"]["resources"]["mysecurity_group"]["properties"]["name"] = user_id + "-security_group" + str(instance_num) # 보안그룹 name 설정
    print(json.dumps(template_data))

    return(json.dumps(template_data))

# def templateImageModify(template):
#     with open(template, 'r') as f:
#         template_data = json.load(f)
#     print(json.dumps(template_data))

#templateImageModify("templates/cirros.json", "user1", "instance_1", "m1.nano", ["https", "apache2"], 2)
#templateFlavorModify("templates/cirros.json", 3)
import json

# 램, 디스크, 이미지, 네트워크 이름, 키페어 네임,


def templateImageModify(template, user_stack_num, flavor):  # template 파일, 유저가 생성할 스택(인스턴스)의 번호(서수) -> 스택 번호 말고 이름 등을 받아올 수도 있음.
    with open(template, 'r') as f:
        template_data = json.load(f)
    template_data["stack_name"] = template_data["stack_name"] + str(user_stack_num)
    template_data["template"]["resources"]["mybox"]["properties"]["name"] = template_data["template"]["resources"]["mybox"]["properties"]["name"] + str(user_stack_num)
    template_data["template"]["resources"]["mybox"]["properties"]["flavor"] = flavor
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

templateImageModify('templates\centos.json', 2)
from enum import Enum
import glob
import importlib
import os
from posixpath import basename
import random
import re
import time
from xml.etree.ElementTree import tostring
from gz.transport13 import Node
import subprocess
from gz.msgs10.stringmsg_pb2 import StringMsg
from gz.msgs10.stringmsg_v_pb2 import StringMsg_V
from gz.msgs10.pose_pb2 import Pose
from gz.msgs10.entity_factory_pb2 import EntityFactory
from gz.msgs10.boolean_pb2 import Boolean
from gz.msgs10.empty_pb2 import Empty
from gz.msgs10.scene_pb2 import Scene
from gz.msgs10.entity_pb2 import Entity
from gz.msgs10.model_pb2 import Model
from gz.msgs10.sdf_generator_config_pb2 import SdfGeneratorConfig
from gz.msgs10.entity_plugin_v_pb2 import EntityPlugin_V
from gz.msgs10.plugin_pb2 import Plugin
from gz.msgs10.parameter_name_pb2 import ParameterName
from gz.msgs10.parameter_value_pb2 import ParameterValue
import xml
from modelsmith import RootGen, ModelGen, POSE, PLUGIN_DIR
import json
from lxml import etree
from lxml.etree import tostring
import randomproto


from plugin_mining import PluginMiner
#import func_timeout


DIR = '/usr/share/gz/gz-msgs10/'
MAX_MODEL_NUM = 20
NUM_ARM = 7 # dirty, should be calculated, not assigned
RANDPROTO_TIMEOUT = 10

import fcntl

def load_builtin(filename):
    with open(filename) as f:
        l = f.read().splitlines()

    return {re.sub(r"/world/.*?/", r"/world/{world_name}/", entry) for entry in l}

def non_blocking_read(fd):
    # Make the file non-blocking
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    output = []
    while True:
        try:
            chunk = os.read(fd, 4096).decode()
            if chunk:
                output.append(chunk)
            else:
                break
        except BlockingIOError:
            # No more data available
            break
    return ''.join(output)

class ServiceParam:
    def __init__(self, service_name, request, req_type, rep_type, timeout=10000):
        self.service_name = service_name
        self.request = request
        self.req_type = req_type
        self.rep_type = rep_type
        self.timeout = timeout

class TopicParam:
    def __init__(self, topic_name, type_name, type_class, publisher, message, timeout=10000):
        self.topic_name = topic_name
        self.type_name = type_name
        self.type_class = type_class
        self.publisher = publisher
        self.message = message
        self.timeout = timeout

class GzCommandType(Enum):
    SERVICE = 1
    TOPIC = 2


class MessageTypeConvert:
    def __init__(self, directory=DIR):
        #self.file_prefix_list = [basename(i)[:-3] for i in glob(f"{DIR}/*.py")]
        self.pb2_modules = list()
        # for file in self.file_prefix_list:
        #     if "__init__" in file:
        #         continue
        #     try:
        #         self.pb2_modules.append(importlib.import_module(f"gz.msgs10.{file}"))
        #     except:
        #         print(f"error processing gz.msgs10.{file}")

    def get_class_type(self, type_name):
        if type_name.startswith("gz.msgs."):
            type_name_stripped = type_name.split(".")[-1]
            class_type = None
            for module in self.pb2_modules:
                try:
                    class_type = getattr(module, type_name_stripped)
                    break
                except:
                    continue

            return class_type
        else:
            return None
        



        
        
        



class GzCommand:
    def __init__(self, gz_type, cmd, use_text=True):
        self.gz_type = gz_type
        self.use_text = use_text
        self.cmd = cmd


    @staticmethod
    def dump_empty(filename):
        with open(filename, "w") as f:
            f.write("")

    def dump(self, filename):
        if self.use_text:
            with open(filename, "w") as f:
                if type(self.cmd) == list:
                    f.write("\n".join(self.cmd))
                else:
                    f.write(self.cmd)


    def execute(self):
        if self.use_text:
            if self.gz_type == GzCommandType.SERVICE:
                if self.cmd:
                    try:
                        ret = subprocess.run(self.cmd, shell=True, stdout=subprocess.PIPE, timeout=10000) # TODO: check this
                        # what to return here?
                        return ret.stdout.decode("utf-8")
                    except:
                        print("DEBUG: subprocess error")
                        return ""
                else:
                    return None
            elif self.gz_type == GzCommandType.TOPIC:
                # traverse gz_topics
                rets = list()
                for topic in self.cmd:
                    try:
                        ret = subprocess.run(topic, shell=True, stdout=subprocess.PIPE, timeout=100)
                        rets.append(ret.stdout.decode("utf-8"))
                    except:
                        print("DEBUG: subprocess error")

                return "\n".join(rets)
        
        else:
            if self.gz_type == GzCommandType.SERVICE:
                node = Node()
                msg_type_convert = MessageTypeConvert()
                service_name = self.cmd.service_name
                request = self.cmd.request
                req_type = self.cmd.req_type
                rep_type = self.cmd.rep_type
                timeout = self.cmd.timeout

                info_list = node.service_info(service_name)
                if not info_list:
                    return ""
                info = random.choice(info_list)
                rep_type = msg_type_convert.get_class_type(info.rep_type_name)
                req_type = msg_type_convert.get_class_type(info.req_type_name)
                if req_type:
                    try:
                        #random_req = func_timeout.func_timeout(RANDPROTO_TIMEOUT, randomproto.randproto, args=[req_type])
                        random_req = "test"
                        req_text = str(random_req).strip()
                        cmd_txt = f"gz service --timeout {self.timeout} -s {service_name} --reptype {info.rep_type_name} --reqtype {info.req_type_name} --req '{req_text}'"
                        result, response = self.node.request(service_name, random_req, req_type, rep_type, self.timeout)

                        return response
                    except:
                        return ""
                else:
                    return ""
            elif self.gz_type == GzCommandType.TOPIC:
                for topic_param in self.cmd:
                    publisher = topic_param.publisher
                    publisher.publish(topic_param.message)

                return ""
            
#use of command
'''if self.use_text:
            return GzCommand(GzCommandType.SERVICE, gz_command, True)
        else:
            gz_service = ServiceParam(service_name, entity_plugin_pb, EntityPlugin_V, Boolean, self.timeout)
            return GzCommand(GzCommandType.SERVICE, gz_service, False)
        cmd_txt = f"gz service --timeout {self.timeout} -s {service_name} --reptype gz.msgs.Boolean --reqtype gz.msgs.EntityFactory --req '{req_txt}'"
            '''


class testUnit:
    def __init__(self,taskName):
       self.currentDay = time.strftime('%Y-%m-%d', time.localtime())
       self.currentTime = time.strftime('%Y-%m-%d_%H:%M:%S', time.localtime())
       self.timeout = 300
       self.plugin_miner = PluginMiner("/usr/share/gz/gz-sim8/worlds")
       self.taskName = taskName
    
    '''class ServiceParam:
    def __init__(self, service_name, request, req_type, rep_type, timeout=10000):
        self.service_name = service_name
        self.request = request
        self.req_type = req_type
        self.rep_type = rep_type
        self.timeout = timeout'''
    
    '''Service providers [Address, Request Message Type, Response Message Type]:
  tcp://172.29.16.209:33625, gz.msgs.Pose, gz.msgs.Boolean'''
    # start gz sim
    def start_gz_sim(self,target_sdf):
        self.target_sdf = target_sdf
        folder_name =  "errors/" + self.currentDay
        if not os.path.exists(folder_name):
    # 如果文件夹不存在，则创建文件夹
            os.makedirs(folder_name)
        self.gz_error_file = folder_name + "/sim_error_" + self.currentTime + ".log"
        self.gz_out_file = folder_name + "/sim_out_" + self.currentTime + ".log"
        cmd_txt = f"gz sim -r -s {target_sdf}"
        start_result = False
        try:
            self.process = subprocess.Popen(cmd_txt.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
        except:
            return False
        start_result = "successfully start gz"
        self.Log(GzCommandType.SERVICE,cmd_txt,start_result)
        self.service_get_world()


    # stop gz sim 
    def stop_gz(self):
        out = non_blocking_read(self.process.stdout.fileno())
        err = non_blocking_read(self.process.stderr.fileno())
        if out:
            with open(f"{self.gz_out_file}", "a") as f:
                # f.write(process.stdout.read().decode("utf-8"))
                f.write(out)
        if err:
            with open(f"{self.gz_error_file}", "a") as f:
                # f.write(process.stderr.read().decode("utf-8"))
                f.write(err)

        
        self.process.terminate()
    

    # service/tiopic_serviceName_time.log :  cmd currentTime result
    def Log(self,commandType,cmd_txt,result):
        fileName = "logs/" + self.currentDay + "/"
        if not os.path.exists(fileName):
    # 如果文件夹不存在，则创建文件夹
            os.makedirs(fileName)
        if commandType == GzCommandType.SERVICE:
            fileName += "SERVICE"
        else:
            fileName += "TOPIC" 
        fileName = fileName + "_" + self.taskName + "_" + self.currentTime + ".log"

        with open(fileName, "a") as file:
            file.write(f"Command: {cmd_txt}     ")
            file.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}      ")
            file.write(f"Result: {result}\n")
            file.write("-" * 40 + "\n")  # 分隔线


    # return current worlds name 
    def service_get_world(self):
        service_name = "/gazebo/worlds"
        request = Empty()
        cmd_txt=f"gz service --timeout 300 -s {service_name}  --reqtype gz.msgs.Empty --reptype gz.msgs.StringMsg_V --req "
        #result =  GzCommand(GzCommandType.SERVICE, cmd_txt,True).execute()
        #return result['data']
        node = Node()
        result, response = node.request(service_name, request, Empty, StringMsg_V, self.timeout)
        self.word = response
        self.Log(GzCommandType.SERVICE,cmd_txt,response)
        return result, response


    # get parameter name
    def service_get_parameter(self,paraName=""):
        world_name = self.word.data[0]
        self.world_name = world_name
        service_name = f"/world/{self.world_name}/get_parameter"

        scene = self.service_scene_info()
        # print(f"scene.model: {scene.model}")
        

        request = ParameterName()
        request.name = paraName
        req_txt = str(request).replace("\n","")
        cmd_txt = f"gz service --timeout 300 -s {service_name}  --reqtype gz.msgs.ParameterName --reptype gz.msgs.ParameterValue --req '{req_txt}' "
        #print(cmd_txt)

        request = ParameterName()
        node = Node()
        result, response = node.request(service_name, request, ParameterName, ParameterValue, 300)

        print(response.data)
        #result =  GzCommand(GzCommandType.SERVICE, cmd_txt,True).execute()
        #self.Log(GzCommandType.SERVICE,cmd_txt,result)


    # random set mdoesl position
    def servic_set_pose(self,pose_max=POSE,pose_min=-POSE):
        world_name = self.word.data[0]
        self.world_name = world_name
        service_name = f"/world/{self.world_name}/set_pose"

        scene = self.service_scene_info()
        # print(f"scene.model: {scene.model}")
        # 1. get random model

        available_models = scene.model
        # print(f"available_models: {available_models}, world_name: {self.world_name}")
        if available_models:
            model = random.choice(available_models)
        else:
            return None
        

        request = Pose()
        request.position.x = random.random() * (pose_max - pose_min) + pose_min
        request.position.y = random.random() * (pose_max - pose_min) + pose_min
        request.position.z = random.random() * (pose_max - pose_min) + pose_min
        request.name = model.name
        req_txt = str(request).replace("\n","")
        cmd_txt = f"gz service --timeout 300 -s {service_name}  --reqtype gz.msgs.Pose --reptype gz.msgs.Boolean --req '{req_txt}' "
        #print(cmd_txt)
        result =  GzCommand(GzCommandType.SERVICE, cmd_txt,True).execute()
        self.Log(GzCommandType.SERVICE,cmd_txt,result)


    # return models and their links 
    def service_scene_info(self):
        world_name = self.word.data[0]
        self.world_name = world_name
        node = Node()
        service_name = f"/world/{self.world_name}/scene/info"
        cmd_txt=f"gz service -s {service_name}  --reqtype gz.msgs.Empty --reptype gz.msgs.Scene --req "
        #result = Scene()
        #result =  GzCommand(GzCommandType.SERVICE, cmd_txt,True).execute()
        #self.resultLog(GzCommandType.SERVICE,service_name.replace("/","_"),cmd_txt,result)
        reserved_models = {"ground_model", "ceiling_model", "west_model", "east_model", "north_model", "south_model"}
        request = Empty()
        node = Node()
        result, response = node.request(service_name, request, Empty, Scene, 300)
        #self.resultLog(GzCommandType.SERVICE,service_name.replace("/","_"),cmd_txt,response)
        #model model.name model.link

        models = dict()
        for m in response.model:
            #print(m.id)
            link_list = list()
            #print(m.collision)
            #print(m.joint)
            for l in m.link :
                link_list.append(l.name)
            models[m.name+ "_" + str(m.id)] = link_list
        json_data = json.dumps(models)

        #print(json_data)
        self.Log(GzCommandType.SERVICE,cmd_txt,json_data)
        return response
    

    # add plugin to a random model
    def service_add_random_plugin(self,use_txt):
        # 0. get world name
        world_name = self.word.data[0]
        scene = self.service_scene_info()
        # print(f"scene.model: {scene.model}")
        # 1. get random model

        available_models = scene.model
        # print(f"available_models: {available_models}, world_name: {self.world_name}")
        if available_models:
            model = random.choice(available_models)
            model_id = model.id
        else:
            return None
        # 2. get random plugin
        plugin = random.choice(self.plugin_miner.plugins_within_model)
        filename = plugin.get("filename")
        name = plugin.get("name")
        innerxml = "\n".join([tostring(c).decode("utf-8") for c in plugin.getchildren()])

        entity_plugin_pb = EntityPlugin_V()
        plugin_pb = Plugin()
        plugin_pb.filename = filename
        plugin_pb.name = name
        plugin_pb.innerxml = innerxml
        entity_plugin_pb.entity.id = model_id
        entity_plugin_pb.plugins.append(plugin_pb)
        # 3. generate gz command
        service_name = f"/world/{world_name}/entity/system/add"
        gz_command = f"gz service --timeout {self.timeout} -s {service_name} --reptype gz.msgs.Boolean --reqtype gz.msgs.EntityPlugin_V --req '{str(entity_plugin_pb)}'"
        # 4. return gz command

        if use_txt:
            result = GzCommand(GzCommandType.SERVICE, gz_command, True).execute()
        else:
            gz_service = ServiceParam(service_name, entity_plugin_pb, EntityPlugin_V, Boolean, self.timeout)
            result = GzCommand(GzCommandType.SERVICE, gz_service, False).execute()
        self.Log(GzCommandType.SERVICE,gz_command,result)
        return result
    

    # change collistion volume and mass
    def changeCollision(self,target_sdf):

        with open(target_sdf) as f:
            txt = f.read()

        tree = etree.XML(txt)
        collistions = tree.xpath("//collision")
        sizes = tree.xpath("//size")
        for size in sizes:
            sizeZ = random.random()
            print(size.text)
            sizeList = size.text.split()
            newSize = ""
            for i in range(2):
                newSize += sizeList[i]
                newSize += " "
            newSize += str(sizeZ)
            print(newSize)

        # for c in collistions:
        #     print(c.get('name'))
        # mass = tree.xpath("//mass")
        # for m in mass:
        #     print(m.text)
            
    

        # tree = xml.etree.ElementTree.parse(target_sdf)  # 假设你的文件名为sdf.xml
        # root = tree.getroot()
        # #print(root.findall("collision"))

        # # 如果你还想查看每个子节点的属性，可以这样做：
        # fir_children = list(root)
        # #print(children)

        # #two ways to change lrauy, change the size of model, change the waterdensity
        # #change lrauy
        # for sec_child in fir_children:
        #     #print(f"Tag: {child.tag}")
        #     #print(list(child))
        #     for tir_child in sec_child:
        #         #print(list(c))
        #         #print(f"    Tag: {c.tag}")
        #         for four_child in tir_child:
        #             #print(list(cc))
        #             if four_child.tag == "collision":
        #                 #print(cc)
        #                 #print(cc.get("size"))
        #                 for fiv_child in four_child:
        #                     #print(ccc)
        #                     for six_child in fiv_child:
        #                         #print(cccc)
        #                         for sev_child in six_child:
        #                             """print(f"Tag: {sec_child.tag}")
        #                             print(f"    Tag: {tir_child.tag}")
        #                             print(f"        Tag: {four_child.tag}")
        #                             print(f"            Tag: {fiv_child.tag}")
        #                             print(f"                Tag: {six_child.tag}")
        #                             print(f"                    Tag: {sev_child.tag}")
        #                             print(sev_child.text)"""
        #                             sev_child.text = "2 0.3 0.26"
                                    
        # tree.write("/home/plume/gazebo_maritime/models/my_lrauv/end.sdf",encoding='utf-8', xml_declaration=True)                 


    # change water denstity
    def changeWaterDensity(self):
        tree = xml.etree.ElementTree.parse(self.target_sdf)  # 假设你的文件名为sdf.xml
        root = tree.getroot()

        fir_children = list(root)

        print(fir_children)
        for sec_chileren in fir_children:
            print(sec_chileren)
            for tir_children in sec_chileren:
                print(tir_children)


    # get random service cmd
    def randomService(self, service_name=""):
        node = Node()
        msg_type_convert = MessageTypeConvert()
        if not service_name:
            service_list = node.service_list()
            if not service_list:
                return None
            service_name = random.choice(service_list)
        
        # if self.skipped and service_name in self.skipped:
        #     print(self.skipped, service_name)
        #     print("DEBUG: should not be here")
        #     return None
        # print(f"\tservice name: {service_name}")
        service_list = node.service_list()
        info_list = node.service_info(service_name)
        print("DEBUG: got here x", service_list, info_list)
        if not info_list:
            return None
        print("DEBUG: got here4")
        info = random.choice(info_list)
        rep_type = msg_type_convert.get_class_type(info.rep_type_name)
        req_type = msg_type_convert.get_class_type(info.req_type_name)
        print("DEBUG: got here5")
        if req_type:
            try:
                print("DEBUG: got here6")
                random_req = randomproto.randproto(req_type)
                print("DEBUG: got here7")
                req_text = str(random_req).strip()
                print("DEBUG: got here8")
                cmd_txt = f"gz service --timeout {self.timeout} -s {service_name} --reptype {info.rep_type_name} --reqtype {info.req_type_name} --req '{req_text}'"
                #gz_service = ServiceParam(service_name, random_req, req_type, rep_type, self.timeout)
                print("DEBUG: got here9")

                if self.use_text:
                    return GzCommand(GzCommandType.SERVICE, cmd_txt, True)
                #else:
                    #return GzCommand(GzCommandType.SERVICE, gz_service, False)

                # TODO: remove explicit call, just return something like gz_service
                # result, response = self.node.request(service_name, random_req, req_type, rep_type, self.timeout)

                # return cmd_txt, result, response
            except:
                return None
                # return "", None, None
        else:
            return None
            # return "", None, None


    # get random topic cmd
    def randomTopic(self):
        msg_type_convert = MessageTypeConvert()
        if not topic_name:
            topic_list = self.node.topic_list()
            if not topic_list:
                return None
            topic_name = random.choice(topic_list)
        if "/scene/info" in topic_name:
            # Scene string triggers argument list too long error
            return None
        info_list = self.node.topic_info(topic_name)
        if not info_list:
            return None
        info = random.choice(info_list)
        cmd_txts = list()
        gz_topics = list()

        for publisher in info:
            type_name = publisher.msg_type_name
            type_class = msg_type_convert.get_class_type(type_name)
            # print(f"DEBUG: type_name: {type_name} type_class: {type_class}")
            pub = self.node.advertise(topic_name, type_class)
            try:
                message = randomproto.randproto(type_class)
                # def __init__(self, topic_name, type_name, type_class, publisher, message, timeout=10000):
                gz_topic = TopicParam(topic_name, type_name, type_class, pub, message)
                gz_topics.append(gz_topic)

                # TODO: remove explicit call, just return something like gz_topics at the end
                # print(message)
                cmd_txt = f"gz topic -t {topic_name} -m {type_name} -p '{message}'"
                pub.publish(message)
                cmd_txts.append(cmd_txt)

            except:
                pass

        if self.use_text:
            return GzCommand(GzCommandType.TOPIC, cmd_txts, True)
        else:
            return GzCommand(GzCommandType.TOPIC, gz_topics, False)
        # return cmd_txts, None, None
        


if __name__ == "__main__":
    test = testUnit("test_lrauv")
    #test.start_gz_sim("/home/plume/Desktop/test.sdf")
    #test.start_gz_sim("/usr/share/gz/gz-sim8/worlds/shapes.sdf")
    test.start_gz_sim("/home/plume/gazebo_maritime/worlds/buoyant_lrauv.sdf")
    #test.start_gz_sim("/home/plume/gazebo_maritime/models/my_lrauv/model.sdf")
    time.sleep(3)
    #cmd_txt1 = f"gz service -s /world/test/state --reqtype gz.msgs.Empty --reptype gz.msgs.SerializedStepMap --req"
    #cmd_txt2 = f"gz service -s /world/test/sysyem/info --reqtype gz.msgs.Empty --reptype gz.msgs.EntityPlugin_V --req"
    for i in range(1):
        #test.service_scene_info()
        #test.service_add_random_plugin(True)
        #test.changeCollision("/home/plume/gazebo_maritime/models/my_lrauv/model.sdf")
        #test.servic_set_pose()
        #test.service_get_parameter("mass")
        test.randomService()
        #print(test.service_get_worlds())
        #test.servic_set_pose()
        #test.changeWaterDensity()
        #test.servic_set_pose("vertical_fins")
        #print("hello 'world'")
    test.stop_gz()
    #print(test.getWorld()[1])
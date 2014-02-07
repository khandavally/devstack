###
import subprocess as sub
import ConfigParser
import os
import sys

class Command_prompt():

    """ Function to execute the Linux commands """
    def execute_terminal_command(self, inpu):
        self.read = sub.Popen(inpu, stdout=sub.PIPE, shell=True)
        (self.output,  self.error) = self.read.communicate()
        return self.output

class Generate_Conf_parameters():

    """ Function to Prepare arguments for Nova, Keystone Files """
    def generate_arguments(self, data, service):
        tmp_data = data.split(",")
        result = ""
        for i in range(len(tmp_data)):
           tmp = tmp_data[i].split(".")
           del tmp[0]
           join_data = ".".join((str(k)) for k in tmp)
           if service == "KEYSTONE":
              result = join_data + "," + result
           elif service == "NOVA":
              result = join_data+":"+join_data+".notify_decorator" + "," + result
        return result[:-1]


class Read_conf():
    name = ""
    product_id = ""
    vendor_id = ""
    directory = ""
    modules = ""
    nova_modules = ""
    keystone_modules = ""
    horizon_modules = ""
    init_modules = ""
    cmd = ['sudo cp', 'sudo chmod 777', 'cd']

    def readfile(self,read_dir, filename):
        """ Read Input parameters from the input.conf files """
        self.read_dir = read_dir
        self.filename = filename
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.filename)
        try:
            #Read_conf.name = str(self.config.get('DEFAULT', 'NAME'))
            #Read_conf.product_id = str(self.config.get('DEFAULT', 'PRODUCT_ID'))
            #Read_conf.vendor_id = str(self.config.get('DEFAULT', 'VENDOR_ID'))
            Read_conf.directory = self.config.get('DEFAULT','ROOT_DIRECTORY')
            Read_conf.horizon_directory = self.config.get('DEFAULT','HORIZON_DIRECTORY')
            Read_conf.nova_modules = self.config.get('DEFAULT','NOVA_MODULES')
            #Read_conf.keystone_modules = self.config.get('DEFAULT','KEYSTONE_MODULES')
            Read_conf.init_modules = self.config.get('DEFAULT','INIT_MODULES')
            Read_conf.class_modules = self.config.get('DEFAULT','CLASS_MODULES')
        except ConfigParser.NoOptionError as ex:
            print ex
            return 0
        except ConfigParser.AttributeError as ex:
            print ex
            return 0
        finally:
            return str(Read_conf.name)

    def nova_writefile(self):
        """ Write the Nova Configuration File here """

        self.config = ConfigParser.ConfigParser()
        self.config.read("/etc/nova/nova.conf")
        self.pci_passthrough_whitelist = '[{"vendor_id":"'+ "8086" +'", "product_id":"'+ "0442"+'"}]'
        self.pci_alias = '{"vendor_id": "'+"8086"+'" , "product_id": "'+"0442"+'" , "name":"'+ "CaveCreek"+'" }'
        self.config.set('DEFAULT', 'pci_passthrough_whitelist', self.pci_passthrough_whitelist )
        self.config.set('DEFAULT', 'pci_alias', self.pci_alias )
        self.config.set('DEFAULT','monkey_patch','True')
        #input_obj = str(Read_conf.nova_modules).split(",")
        #input_obj = ",".join((str(k)+":"+str(k)+".notify_decorator") for k in input_obj)
        write_arguments = Generate_Conf_parameters().generate_arguments(str(Read_conf.nova_modules),"NOVA") 
        self.config.set('DEFAULT', 'monkey_patch_modules', write_arguments)
        with open('/etc/nova/nova.conf', 'wb') as configfile:
                self.config.write(configfile)
        print "Nova Configuration writing completed successfully"
        return 1

    def keystone_writefile(self):
        """Write the Keystone config file from here"""
        write_arguments = Generate_Conf_parameters().generate_arguments(str(Read_conf.keystone_modules),"KEYSTONE")
        self.config = ConfigParser.ConfigParser()
        self.config.read("/etc/keystone/keystone.conf")
        self.config.set('DEFAULT','onready',write_arguments)
        with open('/etc/keystone/keystone.conf', 'wb') as configfile:
                self.config.write(configfile)
        print "Keystone Configuration writing completed successfully"
        return 1

    def concat_service_files(self):
        """ Make a List of Nova , Keystone Files """
        if Read_conf.nova_modules:
            Read_conf.modules = Read_conf.nova_modules
            if Read_conf.keystone_modules:
                Read_conf.modules = Read_conf.modules+","+Read_conf.keystone_modules
                #if Read_conf.horizon_modules:
                #    Read_conf.modules = Read_conf.modules+","+Read_conf.horizon_modules
        
        if (Read_conf.directory != "" and Read_conf.modules != ""):
            input_list = str(Read_conf.modules).split(",")
            Read_conf().copy_module_files(input_list,"SERVICE")

        """ Copy the INIT modules and update the init.py file """
        if Read_conf.init_modules:
            input_list = str(Read_conf.init_modules).split(",")
            Read_conf().copy_module_files(input_list,"INIT")

        else:
            print "Unable to move files in INIT module to directory"

			
	""" Copy the CLASS modules """
        if Read_conf.class_modules:
            input_list = str(Read_conf.class_modules).split(",")
            Read_conf().copy_module_files(input_list,"CLASS")	
		
            
        else:
            print "Unable to move files in CLASS module to directory"

        return 1

    """ Update the Init Package files """
    def init_update_file(self, directory, file_type, input_arg):
        file_path = str(directory)+"__init__.py"
        with open(file_path, 'r') as content_file:
            content = str(content_file.read()).find(input_arg)
            if content == -1:
                with open(file_path, 'a') as content_file:
                    content = content_file.write(input_arg)
                print "writing init file inside %s " % str(file_path)
            else:
                print "Module already imported in the init file %s " % input_arg


    """ Copy modules to the concerned directory and change the permission of file """
    def copy_module_files(self,input_list,file_type):

        obj = Command_prompt()
        for i in range(len(input_list)):
            
                get_destination_dir = str(input_list[i]).split(".")
                file_name = str(get_destination_dir[-1])
                del get_destination_dir[-1]
                get_destination_dir = "/".join(str(k) for k in get_destination_dir)
                
                """ check horizon file or service files and decide the root directory to be copied """
                if get_destination_dir.find("horizon") == -1:
                	final_dir = Read_conf.directory+"/"+get_destination_dir+"/"
                else:
                	final_dir = Read_conf.horizon_directory+"/"+get_destination_dir+"/"

                """ Copy files to the concern directory """
                copy_cmd = Read_conf.cmd[0]+chr(32)+str(os.getcwd())+"/"+str(input_list[i]).split(".")[-1]+".py"+chr(32)+final_dir
                op = obj.execute_terminal_command(copy_cmd)
                print "Copying %s to directory" % (copy_cmd)

                """ change the file permission in destination directory """
                file_path = str(Read_conf.directory)+"/"+str(input_list[i]).replace(".", "/")
                change_cmd = Read_conf.cmd[1]+chr(32)+file_path+".py"
                op = obj.execute_terminal_command(change_cmd)
                print "File permission changed"

                if file_type == "INIT":
                    input_statement = "import "+str(file_name)
                    Read_conf().init_update_file(final_dir, file_type, input_statement)


class Create_Flavors():

    policy_commands = ['ls .. | grep openrc','source ../openrc','nova-manage instance_type list']
    flavor_cmd = ['nova-manage instance_type create ', 'nova-manage instance_type set_key ']
    flavor_name = ['QA.nano ','QA.small ','QA.medium ','QA.large ','QA.xlarge ']
    #memory(MB),cpu,storage(GB),Ephemeral(GB),flavorid,swap(MB),number_of_vf
    flavor_spec = [['64,1,0,0,10,0,1,'],
                   ['512,1,20,0,11,0,2,'],
                   ['1024,2,40,0,12,0,3,'],
                   ['2048,4,80,0,13,0,4,'],
                   ['4096,8,160,0,14,0,5,']]
    flavor_ex_spec = ['pci_passthrough:alias ','vendor_id', 'product_id']

    def __init__(self, pci_alias_name):
        self.pci_alias_name = pci_alias_name
        self.pci_alias_list = []
        self.pci_alias_list.append('pci_passthrough:alias')

    def update_extra_specs(self):
        self.cur_dir = str(os.getcwd()).split("/") # Get current working directory
        if self.cur_dir[-2] == "devstack":
            print "Inside Devstack directory"
            obj = Command_prompt()
            self.chk_file_name = obj.execute_terminal_command(Create_Flavors.policy_commands[0]) # check openrc file inside the devstack directory
            if self.chk_file_name[0:6] == "openrc":
                chk_source = obj.execute_terminal_command(Create_Flavors.policy_commands[1]) # import the openrcfile
                if len(Create_Flavors.flavor_name) == len(Create_Flavors.flavor_spec):
                    for i in range(len(Create_Flavors.flavor_name)):
                        insert_flavor = str(Create_Flavors.flavor_cmd[0])+ str(Create_Flavors.flavor_name[i]) + str(Create_Flavors.flavor_spec[i][0].replace(",",chr(32)))
                        create_flavors = str(Create_Flavors.flavor_name[i])+str(obj.execute_terminal_command(insert_flavor)).split("\n")[0]  # Create Flavors
                        print create_flavors
                        print str(Create_Flavors.flavor_spec[i]).split(",")[6]
                        if create_flavors.find("exists.") == -1:  # if flavor not available already then insert extraspecs
                                insert_spec = str(Create_Flavors.flavor_cmd[1])+ str(Create_Flavors.flavor_name[i]).strip()+chr(32)+Create_Flavors.flavor_ex_spec[0]+chr(32)+str(self.pci_alias_name)+":"+str(Create_Flavors.flavor_spec[i]).split(",")[6]
                                create_specs = obj.execute_terminal_command(insert_spec)
                                print create_specs
                    return 1
        else:
            print "Keep Inside the Devstack directory and execute the script"
        return "Script Executed Successfully"


class KeystonePolicy():
      tenant_name =['demouser','demouser1','demouser2','demouser3','demouser4','demouser5','demouser6']
      tenant_policy = ['Exclusive=1','Policy1=2','Policy2=3','Policy3=4','Policy4=5','Policy5=6','Policy6=7']
      policy_create = ['ls | grep creds','source creds','keystone tenant-create --name %s --description %s']

      def create_policy(self):
          obj_command = Command_prompt()
          self.chk_file_name = obj_command.execute_terminal_command(KeystonePolicy.policy_create[0])          
          if self.chk_file_name[0:5]=="creds":
              chk_source = obj_command.execute_terminal_command(KeystonePolicy.policy_create[1])
              if (len(KeystonePolicy.tenant_name) == len(KeystonePolicy.tenant_policy)):
                  input_args = KeystonePolicy.policy_create[2]
                  for i in range(len(KeystonePolicy.tenant_name)):
                      tenant_policy_set = input_args % (str(KeystonePolicy.tenant_name[i]),str(KeystonePolicy.tenant_policy[i]))
                      output = obj_command.execute_terminal_command(tenant_policy_set)
                      print output




if __name__ == "__main__":
    print "Main function is called"

    """  Update the list of PCI Devices inside the Nova configuration File using given input file"""
    current_dir = str(os.getcwd())
    file_name = sys.argv[1]
    pci_alias_name = Read_conf().readfile(os.getcwd(), file_name)
    obj = KeystonePolicy.create_policy(KeystonePolicy())

    """
     Create Default Flavors and Add Extra Specifications
    """
    if (pci_alias_name):
        print "Writing Nova Configuration Files"
        write_file_nova = Read_conf().nova_writefile()
        print "Writing Keystone Configuration Files"
        write_file_keystone = Read_conf().keystone_writefile()
        if (write_file_nova == 1 and write_file_keystone == 1):
            copy_file = Read_conf().concat_service_files()
            if copy_file:
                flavor_list = Create_Flavors(pci_alias_name).update_extra_specs()
                print "Finished"
            else:
                print "Failed to create flavors"
        else:
            print "Failed to create flavors"
    else:
        print "Failed to write Nova configuration Files"
        print "Script Completed"
  

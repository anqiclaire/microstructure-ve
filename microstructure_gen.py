# This script writes the generate_microstructure.m file that calls 
# CreateAglom2D.m to generate microstructures and uses system calls to run the
# .m file. The output microstructures will be saved in .mat files with filenames
# specified in this script.
import json
import os
import uuid
import subprocess
import csv
from scipy.io import loadmat

class microstructure_gen(object):
    def __init__(self, json_file='params_mat.json', data_dir='./data'):
        self.jobs = []
        self.params = {'ParRu','ParRv','pix','NumAgl','VfAglm','VfFree','scale','seed'}
        # load params-filename map of completed jobs if json_file exists
        if os.path.exists(json_file):
            with open(json_file,'r') as f:
                self.params_filename = json.load(f)
        # otherwise initialize it
        else:
            self.params_filename = {}
        self.json_file = json_file
        # create data_dir if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.data_dir = data_dir

    def generate_mat_name(self, params):
        '''
        Generate a filename for output .mat file with uuid.
        '''
        return f"{int(float(params['ParRu']))}_{int(float(params['ParRv']))}_\
{int(float(params['pix']))}_{int(float(params['NumAgl']))}_\
{float(params['VfAglm'])}_{float(params['VfFree'])}_\
{int(float(params['scale']))}_{int(float(params['seed']))}.mat"

    def add_job(self, params):
        '''
        Add one job to the job list with parameters given in param and assign it
        with a filename for output .mat file.
        '''
        # check if all required parameters are assigned with a value in params
        for par in self.params:
            if par not in params:
                print(f"Please specify {par} in params. Abort.")
                return
        # assign uuid as .mat filename
        filename = self.generate_mat_name(params)
        # update params-filename map
        self.update_params_filename(params, filename)
        # add job to the job list {'filename':'filename.mat','ParRu':8,...}
        job = dict(params)
        job['filename'] = filename
        self.jobs.append(job)
        return

    def write_m_file(self, m_file='generate_microstructure.m'):
        '''
        Write the matlab script that iteratively calls CreateAglom2D.m to 
        generate microstructures with parameters specified in the job list.
        '''
        # stop if the job list is empty
        if len(self.jobs) == 0:
            print("No jobs found. Use .add_job() to add job.")
            return
        # reorganize the job list into parameter lists
        params_list = {par:[] for par in self.params}
        params_list['filename'] = []
        for job in self.jobs:
            for par in params_list:
                params_list[par].append(job[par])
        # start writing
        f = open(m_file, 'w')
        f.write(f'batch = {len(self.jobs)};\n')
        # add data_dir to filename later
        f.write(f'''data_dir = "{self.data_dir+'/'}";\n''')
        # special case, filename is a string array
        f.write(f'''filename = ["{'" "'.join(params_list['filename'])}"];\n''')
        # write other parameters
        for par in params_list:
            if par == 'filename':
                continue
            f.write(f'''{par} = [{' '.join(map(str, params_list[par]))}];\n''')
        # set seed before the loop
        f.write("rng('default');\n")
        f.write('rng(seed(1));\n')
        # write the loop
        f.write('for i = 1:batch\n')
        f.write('    if NumAgl(i) > 1\n')
        f.write('        intervals = sort(rand(1,NumAgl(i)-1));\n')
        f.write('        VfAfl = VfAglm(i)*([intervals,1] - [0,intervals]);\n')
        f.write('    else\n')
        f.write('        VfAfl = [VfAglm(i)];\n')
        f.write('    end\n')
        f.write("    save(strcat(data_dir,'VfAfl_',filename(i)), 'VfAfl');\n")
        f.write('    MS = CreateAglom2DPBC(ParRu(i),ParRv(i),VfAfl,pix(i),NumAgl(i),VfAglm(i),VfFree(i),scale(i),seed(i));\n')
        f.write("    save(strcat(data_dir,filename(i)), 'MS');\n")
        f.write('end\n')
        f.write('exit;\n')
        f.close()
        print(f'{m_file} successfully written.')
        return

    def update_params_filename(self, params, filename):
        '''
        Update the params-filename map for the record.
        '''
        # logging (TODO)
        # save it to params-filename map
        self.params_filename[filename] = params
        # update json
        with open(self.json_file,'w') as f:
            json.dump(self.params_filename, f)
        return

    def run_jobs(self, m_file='generate_microstructure.m'):
        '''
        Run generated matlab script in matlab with a system call.
        '''
        # stop if the job list is empty
        if len(self.jobs) == 0:
            print("No jobs found. Use .add_job() to add job.")
            return
        # stop if the .m file is not found
        if not os.path.exists(m_file):
            print(f"{m_file} not found.")
            return
        # run matlab
        print("Matlab running...")
        # returns the exit code in unix
        exit_code = subprocess.call(f'matlab -nodisplay < {m_file}', shell=True)
        print("Matlab run returned with exit code:", exit_code)
        return

    def load_job_params(self, import_params='batch_jobs.csv'):
        '''
        Load job parameters from a csv file. See batch_job.csv for format ref.
        '''
        if not os.path.exists(import_params):
            print(f"{import_params} not found.")
            return
        with open(import_params,'r') as f:
            reader = csv.DictReader(f)
            # check if the csv file has the correct header row
            if set(reader.fieldnames) != self.params:
                print(f"Please check the header row in {import_params}, it",
                      f"must include all elements of {self.params}.")
                return
            # start reading and add job to the job list
            for row in reader:
                self.add_job(row)
        print(f"{import_params} loaded to the job list.",
            "You can proceed to write_m_file() and run_jobs().",
            f"Remember to clean the {import_params}.")
        return

    def load_and_run(self, import_params='batch_jobs.csv',
        m_file='generate_microstructure.m'):
        '''
        This function combines .load_job_params(), .write_m_file(), and
        .run_jobs().
        '''
        self.load_job_params(import_params)
        self.write_m_file(m_file)
        self.run_jobs(m_file)
        return

    def update_VfAfl(self):
        for filename in self.params_filename:
            VfAfl = loadmat(f'{self.data_dir}/VfAfl_{filename}'
                )['VfAfl'].flatten().tolist()
            self.params_filename[filename]['VfAfl'] = VfAfl
        # update json
        with open(self.json_file,'w') as f:
            json.dump(self.params_filename, f)
        return
        
    def remove_duplicates(self):
        '''
        Remove duplicated microstructures from the params-filename map (json).
        '''
        # first save all microstructures into a dict
        all_ms = {} # microstructure: mat filename
        has_dup = set() # a set to store microstructure mapped to multiple mat filename
        for matfile in self.params_filename:
            ms = loadmat(f'{self.data_dir}/{matfile}')['MS'].tobytes()
            all_ms[ms] = all_ms.get(ms,[])
            all_ms[ms].append(matfile)
            if len(all_ms[ms]) > 1:
                has_dup.add(ms)
        print(f'{len(has_dup)} microstructures has duplicates in {self.data_dir}.')
        # check for microstructures that are mapped to more than 1 mat filename
        # only keep the one with the smallest VfFree
        to_remove = set()
        for ms in has_dup:
            # sort matfile name by VfFree
            all_ms[ms].sort(key=lambda x:float(self.params_filename[x]['VfFree']))
            # skip the first mat filename, start from index 1
            for mat in all_ms[ms][1:]:
                del self.params_filename[mat]
                print(f'removed from json: {self.data_dir}/{mat}')
        # update json
        with open(self.json_file,'w') as f:
            json.dump(self.params_filename, f)
        return



if __name__ == '__main__':
    msgen = microstructure_gen(json_file='test_params_mat.json',data_dir='./test_data')
    # params = {'NumAgl':1, 'VfAglm':0.1, 'VfFree':0.02, 'ParRu':8, 'ParRv':1.5, 'pix':400, 'scale':1, 'seed':7}
    # msgen.add_job(params)
    # params = {'NumAgl':3, 'VfAglm':0.2, 'VfFree':0.03, 'ParRu':7, 'ParRv':1.2, 'pix':300, 'scale':1, 'seed':7}
    # msgen.add_job(params)
    msgen.load_job_params('test_batch_jobs.csv')
    msgen.write_m_file('test_write_m_file.m')
    msgen.run_jobs(m_file='test_write_m_file.m')

# A typical generate_microstructure.m will look like this:
'''
batch = 3;
data_dir = "./data";
filename = ["filename1.mat", "filename2.mat", "filename3.mat"];
ParRu = [1 2 3];
ParRv = [1 2 3];
pix = [1 2 3];
NumAgl = [1 2 3];
VfAglm = [1 2 3];
VfFree = [1 2 3];
scale = [1 1 1];
seed = [7 7 7];

for i = 1:batch
    rng('default');
    rng(seed(i));
    if NumAgl(i) > 1
        intervals = sort(rand(1,NumAgl(i)-1));
        VfAfl = VfAglm(i)*([intervals,1] - [0,intervals]);
    else
        VfAfl = [VfAglm(i)];
    end

    save(strcat(data_dir,'VfAfl_',filename(i)), 'VfAfl');
    MS = CreateAglom2DPBC(ParRu(i),ParRv(i),VfAfl,pix(i),NumAgl(i),VfAglm(i),VfFree(i),scale(i),seed(i));
    save(strcat(data_dir,filename(i)), 'MS');
end
exit;
'''
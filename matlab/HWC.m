classdef HWC
   properties
      auth_data struct
      connect_options weboptions
      auth_filename string
      servername string
      file_directory string
   end
   methods
       function obj = HWC(server)
           [obj, ok_code] = obj.connect(server);
           if ok_code.statusCode ~= 200
               error('Server error')
           end

           obj.file_directory = './files';
           obj.auth_filename = 'auth_config.json';
           if exist(obj.auth_filename, 'file') == 2
               obj = obj.read_auth_config();
           else
               obj = obj.get_auth_data();
           end
           if ~exist(obj.file_directory, 'dir')
               mkdir(obj.file_directory);
           end
           addpath(obj.file_directory)
       end
       function [obj, ok] = connect(obj, server)
           obj.servername = server;
           obj.connect_options = HWC.request_options();

           ok = webread(strcat(obj.servername,'/api/ok'), obj.connect_options);
       end
       function ok = login(obj)
           ok = 1;
           request_msg.auth = obj.auth_data;
           response_msg = webwrite(strcat(obj.servername,'/api/login'), request_msg, obj.connect_options);
           if response_msg.isError
               error(response_msg.message)
               ok=0;
           end

       end
       function obj = read_auth_config(obj)
           fid = fopen(obj.auth_filename);
           str = char(fread(fid,inf)');
           fclose(fid);
           obj.auth_data = jsondecode(str);
           obj.auth_data.id = HWC.validate_student_id(obj.auth_data.id);
       end
       function obj = get_auth_data(obj)
           obj.auth_data = struct;
           fprintf('\n\n***Registration***\n');
           obj.auth_data.name = strip(input('Your full name: ', 's'));
           obj.auth_data.id = str2double(input('Your HDU ID: ', 's'));
           obj.auth_data.id = HWC.validate_student_id(obj.auth_data.id);
           obj.auth_data.email = strip(input('Type your affiliated with university EMail: ', 's'));
           obj.auth_data.password = input('Password: ', 's');
           again_password = input('Retype your password: ', 's');
           if ~strcmp(again_password, obj.auth_data.password)
               error('Password does not match')
           end
           request_msg.auth = obj.auth_data;
           response_msg = webwrite(strcat(obj.servername,'/api/register'), request_msg, obj.connect_options);
           if response_msg.isError
               error(response_msg.message)
           end
           fid=fopen(obj.auth_filename,'w');
           fprintf(fid, '%s', jsonencode(obj.auth_data));
       end
       function task = get_task(obj, number)
           task = nan;
           request_msg.auth = obj.auth_data;
           request_msg.number = number;
           response_msg = webwrite(strcat(obj.servername,'/api/gettask'), request_msg, obj.connect_options);
           if response_msg.isError
               error(response_msg.message)
           end
           task = struct();
           task.number = number;
           task.parameters = response_msg.data.parameters;
           task.answers = response_msg.data.answers;
           task.files = response_msg.data.files;
           if isempty(task.files)
               return
           elseif ischar(task.files) || isstring(task.files)
               file_list = cellstr(task.files);
           elseif iscell(task.files)
               file_list = task.files;
           else
               error('HWC:InvalidFiles', 'Unexpected task file list')
           end
           for i = 1:numel(file_list)
               [~, name, ext] = fileparts(file_list{i});
               websave(fullfile(obj.file_directory, [name ext]), ...
                   strcat(obj.servername, file_list{i}), obj.connect_options);
           end
       end
       function score = send_task(obj, task)
           request_msg.auth = obj.auth_data;
           request_msg.task = task;
           response_msg = webwrite(strcat(obj.servername,'/api/send_task'), request_msg, obj.connect_options);
           if response_msg.isError
               error(response_msg.message)
           end
           if response_msg.message ~= ""
               disp(response_msg.message)
           end
           score = response_msg.data;
       end
   end
   methods (Static)
       function options = request_options()
           options = weboptions('ContentType', 'auto', ...
               'CharacterEncoding', 'UTF-8', 'Timeout', 30, ...
               'CertificateFilename', 'default');
       end
       function id = validate_student_id(id)
           if ~isnumeric(id) || ~isscalar(id) || ~isreal(id) || ...
                   ~isfinite(id) || id < 1 || id ~= fix(id) || id >= flintmax
               error('HWC:InvalidStudentId', 'Student ID must be a positive whole number');
           end
       end
   end
end

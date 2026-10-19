function hwc = hwc_connect(server)
    if nargin == 0
        server = 'https://dss.hdu.vedyakov.com';
    end
    hwc = nan;
    options = weboptions('ContentType', 'auto', ...
        'CharacterEncoding', 'UTF-8', 'Timeout', 30, ...
        'CertificateFilename', 'default');
    staging = tempname;
    mkdir(staging);
    cleanup = onCleanup(@() rmdir(staging, 's'));
    try
        version = webread(strcat(server, '/api/matlab/client_version'), options);
        launcher_version = webread(strcat(server, '/api/matlab/launcher_version'), options);
        if ~strcmp(file_md5('HWC.m'), version.data.md5) || ...
                ~strcmp(file_md5('hwc_connect.m'), launcher_version.data.md5)
            names = {'HWC.m', 'hwc_connect.m', 'hwc_reset.m'};
            for i = 1:numel(names)
                websave(fullfile(staging, names{i}), ...
                    strcat(server, '/clients/hwc-matlab-client/', names{i}), options);
            end
            if ~strcmp(file_md5(fullfile(staging, 'HWC.m')), version.data.md5) || ...
                    ~strcmp(file_md5(fullfile(staging, 'hwc_connect.m')), launcher_version.data.md5)
                error('HWC:ClientUpdate', 'Client files do not match the published version');
            end
            for i = 1:numel(names)
                [ok, message] = movefile(fullfile(staging, names{i}), names{i}, 'f');
                if ~ok
                    error('HWC:ClientUpdate', '%s', message);
                end
            end
            rehash;
            disp('Client updated. Clear existing HWC objects and run hwc_connect again.');
            return
        end
    catch err
        warning('HWC:ConnectionFailed', 'Cannot update the client securely: %s', err.message);
        return
    end
    hwc = HWC(server);
    if ~hwc.login()
        error('HWC:AuthenticationFailed', 'Authentication failed');
    end
    disp('Connection established');
end

function hash = file_md5(filename)
    hash = '';
    fid = fopen(filename, 'rb');
    if fid < 0
        return
    end
    cleanup = onCleanup(@() fclose(fid));
    bytes = fread(fid, Inf, '*uint8');
    import java.security.*;
    import java.math.*;
    import java.lang.String;
    md = MessageDigest.getInstance('MD5');
    digest = md.digest(double(bytes));
    hash = char(String.format('%032x', BigInteger(1, digest)));
end

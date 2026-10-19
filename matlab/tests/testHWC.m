function tests = testHWC
    tests = functiontests(localfunctions);
end
function testOrdinaryStudentIds(testCase)
    for id = [1, 19322000, 21322500, 26322000, 99999999]
        verifyEqual(testCase, HWC.validate_student_id(id), id);
        encoded = jsonencode(struct('id', HWC.validate_student_id(id)));
        decoded = jsondecode(encoded);
        verifyEqual(testCase, decoded.id, id);
    end
end
function testInvalidStudentIds(testCase)
    values = {0, -1, 1.5, NaN, Inf, true, [1 2], '26322000', flintmax};
    for i = 1:numel(values)
        verifyError(testCase, @() HWC.validate_student_id(values{i}), 'HWC:InvalidStudentId');
    end
end
function testVerifiedHttpsAndTimeout(testCase)
    options = HWC.request_options();
    verifyEqual(testCase, options.CertificateFilename, 'default');
    verifyEqual(testCase, options.Timeout, 30);
end

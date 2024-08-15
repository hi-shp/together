def check_keywords_in_string(input_string, keywords):
    for keyword in keywords:
        if keyword in input_string:
            return True
    return False

def extract_domain_part(url, domain):
    domain_index = url.find(domain)
    
    if domain_index == -1:
        return url
    
    path_start_index = url.find('/', domain_index + len(domain))
    
    if path_start_index == -1:
        return url
    else:
        return url[:path_start_index]
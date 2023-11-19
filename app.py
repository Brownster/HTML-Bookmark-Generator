from flask import Flask, request, send_file, redirect, url_for, render_template
import os
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = '/tmp/'

non_standard_url_map = {
    'exporter_ems': '/sbc',
    'exporter_ams': ':8443/emlogin',
    'exporter_voiceportal': ':5432'
}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'xlsx', 'xls', 'csv'}

@app.route('/', methods=['GET'])
def index():
    # Render the HTML page for file upload
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the file part is present in the request
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']
        group_name = request.form['group_name']

        # Check if a file is selected and it has the allowed extension
        if file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)

        # Save the uploaded file to a temporary directory
        filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filename)

        try:
            # Filter the exporters from the uploaded file
            filtered_data = filter_exporters(filename, group_name)
        except Exception as e:
            # Handle the exception, possibly by flashing a message to the user
            print("Error processing the file:", e)
            return redirect(request.url)

        # Generate the bookmarks HTML
        bookmarks_html = generate_bookmarks_html(filtered_data)
        
        # Define the filename for the bookmarks HTML file
        processed_filename = f"bookmarks_{group_name}.html"
        processed_filepath = os.path.join(app.config['UPLOAD_FOLDER'], processed_filename)

        # Save the bookmarks HTML to a file
        with open(processed_filepath, 'w', encoding='utf-8') as bookmarks_file:
            bookmarks_file.write(bookmarks_html)

        # Redirect the user to the download route
        return redirect(url_for('download_file', filename=processed_filename))

    # If the request method is not POST or other error conditions
    return 'File upload error'

def filter_exporters(filepath, group_name):
    # Determine the file extension
    file_extension = filepath.rsplit('.', 1)[1].lower()

    # Read the file based on its extension
    if file_extension in ['xlsx', 'xls']:
        df = pd.read_excel(filepath, engine='openpyxl')
    elif file_extension == 'csv':
        df = pd.read_csv(filepath)
    else:
        raise ValueError("Unsupported file type")

    # Define the exporters to look for
    exporters = ['exporter_aes', 'exporter_avayasbc', 'exporter_acm']

    # Filter the DataFrame for rows that contain the specified exporters
    filtered_rows = []
    for exporter in exporters:
        # Check if the exporter columns exist in the DataFrame
        for col in ['Exporter_name_app', 'Exporter_name_app_2']:
            if col in df.columns:
                # Filter rows where the column contains the exporter
                matching_rows = df[df[col].str.contains(exporter, na=False)]
                # Extract necessary information from each row
                for _, row in matching_rows.iterrows():
                    filtered_rows.append({
                        'Group Name': group_name,
                        'Country': row['Country'],
                        'Location': row['Location'],
                        'Exporter Type': exporter,
                        'IP Address': row['IP Address'],
                        'Hostname': row.get('Hostname', 'Unknown')
                    })

    return filtered_rows

def generate_bookmarks_html(filtered_data):
    bookmarks_html = "<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
    bookmarks_html += "<META HTTP-EQUIV=\"Content-Type\" CONTENT=\"text/html; charset=UTF-8\">\n"
    bookmarks_html += "<TITLE>Bookmarks</TITLE>\n"
    bookmarks_html += "<H1>Bookmarks Menu</H1>\n"
    bookmarks_html += "<DL><p>\n"
    
    for group in set(item['Group Name'] for item in filtered_data):
        bookmarks_html += f"    <DT><H3>{group}</H3>\n"
        bookmarks_html += "    <DL><p>\n"
        
        for country in set(item['Country'] for item in filtered_data if item['Group Name'] == group):
            bookmarks_html += f"        <DT><H3>{country}</H3>\n"
            bookmarks_html += "        <DL><p>\n"
            
            for location in set(item['Location'] for item in filtered_data if item['Group Name'] == group and item['Country'] == country):
                bookmarks_html += f"            <DT><H3>{location}</H3>\n"
                bookmarks_html += "            <DL><p>\n"
                
                for item in filtered_data:
                    if item['Group Name'] == group and item['Country'] == country and item['Location'] == location:
                        exporter_type = item['Exporter Type'].split('_')[-1]
                        
                        # Combine exporter type with hostname
                        bookmark_text = f"{exporter_type}-{item['Hostnames']}" 

                        if item['Exporter Type'] in non_standard_url_map:
                            url_part = non_standard_url_map[item['Exporter Type']]
                            url = f"https://{item['IP Address']}{url_part}" if url_part.startswith(':') else f"https://{item['IP Address']}{url_part}"
                        else:
                            url = f"https://{item['IP Address']}"

                        bookmarks_html += f"                <DT><A HREF=\"{url}\">{bookmark_text}</A>\n"
                
                bookmarks_html += "            </DL><p>\n"
            bookmarks_html += "        </DL><p>\n"
        bookmarks_html += "    </DL><p>\n"
    
    bookmarks_html += "</DL><p>\n"
    
    return bookmarks_html


@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    download_folder = app.config['UPLOAD_FOLDER']
    file_path = os.path.join(download_folder, filename)
    
    if not os.path.isfile(file_path):
        return "File not found.", 404

    response = send_file(file_path, as_attachment=True, download_name=filename)
    os.remove(file_path)
    
    return response

if __name__ == '__main__':
    app.run(debug=True)
